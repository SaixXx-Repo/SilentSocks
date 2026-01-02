import pandas as pd
import io
import re

def load_file_content(uploaded_file):
    """
    Load content into a format we can process (BytesIO or just the file object).
    """
    return uploaded_file

def is_customer_file(filename):
    return "kundlista" in filename.lower()

def is_sales_file(filename):
    return "försäljningsstatistik" in filename.lower() or "sales" in filename.lower() or "statistik" in filename.lower()

def process_customer_file(uploaded_file):
    """
    Parse the specific customer list format.
    Header is expected around row 6 (index 5).
    """
    try:
        # Read file, skipping initial metadata rows to get to the header
        # Based on file inspection, header seems to be at row 5 (0-indexed) -> 6th row
        df = pd.read_excel(uploaded_file, header=5)
        
        # Identify standard columns based on Swedish headers seen in file
        # 'Kundnummer', 'Namn', 'Adress', 'Postnummer', 'Postort', 'Land', 'Kundgrupp'
        
        column_map = {
            'Kundnummer': 'customer_number',
            'Namn': 'name',
            'Adress': 'address',
            'Postnummer': 'zip_code',
            'Postort': 'city',
            'Land': 'country',
            'Kundgrupp': 'customer_group'
        }
        
        # Filter columns that exist
        cols_to_keep = [c for c in df.columns if c in column_map]
        df = df[cols_to_keep]
        
        # Rename to db schema
        df = df.rename(columns=column_map)
        
        # Drop rows where customer_number is NaN
        df = df.dropna(subset=['customer_number'])
        
        # Clean data
        df['customer_number'] = df['customer_number'].astype(str).str.strip()
        
        return df
        
    except Exception as e:
        raise ValueError(f"Error processing customer file: {e}")

def process_sales_file(uploaded_file):
    """
    Parse the hierarchical sales statistics file.
    """
    try:
        # Read with no header first to parse structure manually or find the data start
        # Based on inspection, actual data headers for articles seem to start around row 7 or 8 (index 6/7)
        # But the file is hierarchical.
        
        # Let's read the whole file without header to iterate rows
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # Extract date from metadata if possible (row 0 has "Avser perioden" sometimes)
        # For now, we'll try to find the date range or just use current date/filename date
        # If filename has date, use that.
        filename = uploaded_file.name if hasattr(uploaded_file, 'name') else "Unknown"
        # Match pattern: Silent socks YYMMDD...
        # We look for 6 digits after "Silent socks " or just 6 digits that look like a date
        # The file format seen is: Försäljningsstatistik Silent socks 250101-250131.xlsx
        
        # Regex to capture Year(YY), Month(MM), Day(DD)
        # Look for the pattern: Any text -> date -> hyphen
        match = re.search(r'Silent socks\s+(\d{2})(\d{2})(\d{2})', filename, re.IGNORECASE)
        
        if match:
            yy, mm, dd = match.groups()
            year = f"20{yy}"
            month = mm
            # file_date = f"{year}-{month}-{dd}" 
            # Usually we want the month start for consistency, or the actual start date?
            # Previous logic was strict. Let's use the actual start date found.
            file_date = f"{year}-{month}-{dd}"
        else:
            # Fallback: try to find just any 6 digit date pattern
            date_fallback = re.search(r'(\d{2})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})', filename)
            if date_fallback:
                 yy, mm, dd = date_fallback.groups()[0:3]
                 year = f"20{yy}"
                 file_date = f"{year}-{mm}-{dd}"
            else:
                 file_date = pd.Timestamp.now().strftime('%Y-%m-%d')

        records = []
        current_customer_id = None
        
        # Iterate through rows
        # We look for a pattern where Column 0 is a customer number (usually numeric)
        # And patterns where Column 1 is an Article Number
        
        # Found in inspection:
        # Header row for Customer data: Row index 4 (0-based) -> "Kundnr.", "Kundnamn", ...
        # Header row for Article data: Row index 7 -> "Artikelnr.", "Namn", "Antal", ...
        
        start_row = 0
        for i, row in df_raw.iterrows():
            if str(row[0]).strip() == "Kundnr.":
                start_row = i + 1
                break
        
        # Now iterate from start_row
        for i in range(start_row, len(df_raw)):
            row = df_raw.iloc[i]
            col0 = str(row[0]).strip()
            col1 = str(row[1]).strip()
            
            # Skip if it's the "Totalt:" row at the end
            if "totalt" in col1.lower():
                continue

            # Check if it's a Customer Row (Col 0 has value, Col 1 usually NaN or empty)
            # Customer ID is usually numeric (e.g., 100, 10001)
            # IMPORTANT: Sometimes Col 1 is NOT empty if the customer row has total data, 
            # BUT an Article Row will always have a known Article ID format or header text.
            # Looking at sample: Customer Row has Col 1 = NaN.
            if col0.isdigit() and (col1 == 'nan' or col1 == ''):
                current_customer_id = col0
                continue
                
            # Check if it's an Article Row (Col 1 has value)
            # Exclude header rows that might appear repeatedly ("Artikelnr.")
            if "artikelnr" in col1.lower():
                continue
                
            # Ensure we have a customer context
            if current_customer_id and col1 != 'nan' and col1 != '':
                # Map columns based on inspection:
                # 1: Artikelnr
                # 2: Namn (Article Name)
                # 3: Antal (Quantity)
                # 4: Totalt inköpspris
                # 5: TB (snitt) per enhet
                # 6: TB i kr
                # 7: TB i %
                # 8: Försäljning totalt exkl moms
                
                try:
                    article_id = col1
                    article_name = str(row[2])
                    quantity = pd.to_numeric(row[3], errors='coerce')
                    tb_kr = pd.to_numeric(row[6], errors='coerce') # User specifically requested "TB i kr"
                    sales_ex_vat = pd.to_numeric(row[8], errors='coerce')
                    
                    # 1. Format Article ID: 'E' + 5 digits
                    # Remove 'E' if present, convert to int, format back to E00000
                    raw_id = str(article_id).upper().replace('E', '').strip()
                    # Handle potential floats like '9005.0'
                    if '.' in raw_id: 
                         raw_id = raw_id.split('.')[0]
                         
                    if raw_id.isdigit():
                        article_id = f"E{int(raw_id):05d}"
                    else:
                        article_id = f"E{raw_id}" # Fallback
                        
                    # 2. Clean Article Name: Remove everything before "Silent Socks"
                    target_str = "Silent Socks"
                    # Case insensitive search
                    idx = article_name.lower().find(target_str.lower())
                    if idx != -1:
                        # Keep original casing from the found point onwards (assuming match casing implies target casing)
                        # Actually strict requirement: "starts with Silent Socks"
                        # We use the found index to slice.
                        # However, user likely wants "Silent Socks..." casing preserved or fixed?
                        # Let's preserve the "Silent Socks" casing from the string if found, or force it.
                        # Simple slice:
                        article_name = article_name[idx:]
                        
                        # Verify it starts with correct casing if needed, but user just said "cut out before"
                        # If the string was "bla bla silent socks...", result is "silent socks..."
                        # We might want to capitalize 'Silent Socks' properly if it was lowercase.
                        # But simpler is just slice.
                    
                    if pd.notna(quantity) and quantity != 0:
                         records.append({
                             'date': file_date,
                             'customer_number': current_customer_id,
                             'article_id': article_id,
                             'article_name': article_name,
                             'quantity': quantity,
                             'tb_amount': tb_kr if pd.notna(tb_kr) else 0.0,
                             'sales_amount': sales_ex_vat if pd.notna(sales_ex_vat) else 0.0
                         })
                except Exception as e:
                    # Skip malformed rows
                    continue

        return pd.DataFrame(records)

    except Exception as e:
        raise ValueError(f"Error processing sales file: {e}")
