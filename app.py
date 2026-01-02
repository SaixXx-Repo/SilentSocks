import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from database import init_db, save_sales_data, save_customers, get_all_data, get_customer_count, clear_database
from data_processor import process_customer_file, process_sales_file, is_customer_file

# Page config
st.set_page_config(page_title="Sales Analysis", layout="wide")

# Initialize DB
init_db()

st.title("Sales Data Analysis Tool")

# Tabs
tab1, tab2, tab3 = st.tabs(["Import Data", "Dashboard", "AI Analysis"])

# --- TAB 1: IMPORT DATA ---
with tab1:
    st.header("Import Excel Files")
    st.info("Upload 'Kundlista' files to update customer registry, and 'Försäljningsstatistik' files for sales data.")
    
    col_upload, col_action = st.columns([3, 1])
    
    with col_upload:
        uploaded_files = st.file_uploader("Upload Files", type=['xlsx'], accept_multiple_files=True)
        
    with col_action:
        st.write("") # Spacer
        st.write("") 
        if st.button("Clear All Data", type="primary"):
            clear_database()
            st.toast("Database cleared successfully!", icon="🗑️")
            st.rerun()

    if st.button("Process Files"):
        if uploaded_files:
            files_processed = 0
            cust_files = 0
            sales_files = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, file in enumerate(uploaded_files):
                status_text.text(f"Processing {file.name}...")
                try:
                    # Determine file type
                    if is_customer_file(file.name):
                        df = process_customer_file(file)
                        save_customers(df)
                        cust_files += 1
                        st.success(f"Updated customer registry from {file.name} ({len(df)} customers)")
                    else:
                        # Assume sales file
                        df = process_sales_file(file)
                        if not df.empty:
                            save_sales_data(df, file.name)
                            sales_files += 1
                            st.success(f"Imported sales from {file.name} ({len(df)} records)")
                        else:
                            st.warning(f"No valid sales records found in {file.name}")
                            
                    files_processed += 1
                except Exception as e:
                    st.error(f"Error processing {file.name}: {e}")
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
            status_text.text("Processing complete!")
            if files_processed > 0:
                 st.success(f"Done! Processed {cust_files} customer files and {sales_files} sales files.")
        else:
            st.warning("Please upload at least one file.")
            
    # Show stats
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Customers in Registry", get_customer_count())
    with col2:
        df_preview = get_all_data()
        st.metric("Total Sales Records", len(df_preview))

# --- TAB 2: DASHBOARD ---
with tab2:
    st.header("Sales Dashboard")
    
    # Reload data
    df = get_all_data()
    
    if df.empty:
        st.warning("No data available. Please import data first.")
    else:
        # Filters
        st.subheader("Filters")
        
        # Row 1 Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date Filter
            min_date = df['date'].min().date() if not pd.isnull(df['date'].min()) else datetime.date.today()
            max_date = df['date'].max().date() if not pd.isnull(df['date'].max()) else datetime.date.today()
            
            if min_date > max_date: min_date, max_date = max_date, min_date
            
            date_range = st.date_input("Date Range", [min_date, max_date])
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = min_date, max_date

        with col2:
            # Country Filter
            all_countries = ['All'] + sorted(df['country'].fillna('Unknown').unique().tolist())
            selected_country = st.selectbox("Country", all_countries)

        with col3:
            # Customer Group Filter
            all_groups = ['All'] + sorted(df['customer_group'].fillna('Unknown').unique().tolist())
            selected_group = st.selectbox("Customer Group", all_groups)
            
        # Row 2 Filters
        col4, col5, col6 = st.columns(3)
            
        with col4:
            # Customer Type Filter (Derived)
            customer_types = ['All', 'Business', 'Private']
            selected_cust_type = st.selectbox("Customer Type", customer_types)
            
        with col5:
            # Customer Filter (Individual)
            all_customers = ['All'] + sorted(df['customer'].dropna().unique().tolist())
            selected_customer = st.selectbox("Specific Customer", all_customers)

        with col6:
            # Article Filter
            # Create label with ID + Name
            df['article_display'] = df['article_id'].astype(str) + " - " + df['article'].astype(str)
            all_articles = ['All'] + sorted(df['article_display'].dropna().unique().tolist())
            selected_article = st.selectbox("Article", all_articles)

        # Apply filters
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        
        if selected_country != 'All':
            if selected_country == 'Unknown':
                mask = mask & (df['country'].isna())
            else:
                mask = mask & (df['country'] == selected_country)
                
        if selected_group != 'All':
            if selected_group == 'Unknown':
                mask = mask & (df['customer_group'].isna())
            else:
                mask = mask & (df['customer_group'] == selected_group)

        if selected_cust_type != 'All':
            # Logic: Private customers start with '90'
            is_private = df['customer_number'].astype(str).str.strip().str.startswith('90')
            if selected_cust_type == 'Private':
                mask = mask & is_private
            else: # Business
                mask = mask & (~is_private)
                
        if selected_customer != 'All':
            mask = mask & (df['customer'] == selected_customer)

        if selected_article != 'All':
            mask = mask & (df['article_display'] == selected_article)
        
        filtered_df = df[mask]
        
        st.divider()

        if filtered_df.empty:
            st.info("No data matches the selected filters.")
        else:
            # KPIs
            # User mentioned 'TB i kr' is important. We sum that as 'Profit/TB' and Sales as Revenue
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            
            total_rev = filtered_df['sales_amount'].sum()
            total_tb = filtered_df['tb_amount'].sum()
            total_qty = filtered_df['quantity'].sum()
            
            # Calculate Margin
            margin_pct = (total_tb / total_rev * 100) if total_rev > 0 else 0
            
            kpi1.metric("Total Sales (excl VAT)", f"{total_rev:,.0f} kr")
            kpi2.metric("Total TB (Profit)", f"{total_tb:,.0f} kr")
            kpi3.metric("TB Margin %", f"{margin_pct:.1f}%")
            kpi4.metric("Total Qty", f"{total_qty:,.0f}")

            st.divider()
            
            # Row 1 Charts
            c1, c2 = st.columns(2)
            
            with c1:
                # Sales by Country (Map/Bar)
                sales_by_country = filtered_df.groupby('country')['sales_amount'].sum().reset_index().sort_values('sales_amount', ascending=False)
                fig_country = px.bar(sales_by_country, x='sales_amount', y='country', orientation='h', title="Sales by Country")
                fig_country.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_country, use_container_width=True)
                
            with c2:
                # Sales by Customer Group
                sales_by_group = filtered_df.groupby('customer_group')['sales_amount'].sum().reset_index()
                fig_group = px.pie(sales_by_group, values='sales_amount', names='customer_group', title="Sales Share by Customer Group")
                st.plotly_chart(fig_group, use_container_width=True)
            
            # Row 2 Charts
            c3, c4 = st.columns(2)
            
            with c3:
                 # Trend over time
                sales_over_time = filtered_df.groupby('date')['sales_amount'].sum().reset_index().sort_values('date')
                fig_line = px.line(sales_over_time, x='date', y='sales_amount', title="Revenue Trend Over Time")
                st.plotly_chart(fig_line, use_container_width=True)
                
            with c4:
                # Top Customers by TB
                top_cust_tb = filtered_df.groupby('customer')['tb_amount'].sum().reset_index().sort_values('tb_amount', ascending=False).head(10)
                fig_cust_tb = px.bar(top_cust_tb, x='tb_amount', y='customer', orientation='h', title="Top 10 Customers by TB (Profit)")
                fig_cust_tb.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_cust_tb, use_container_width=True)
                
            # Row 3: Article Performance
            st.divider()
            st.subheader("Article Performance")
            
            c5, c6 = st.columns(2)
            
            with c5:
                # Article Sales by Quantity
                # Group by article name (or display name) and sum quantity
                art_qty = filtered_df.groupby('article_display')['quantity'].sum().reset_index().sort_values('quantity', ascending=False)
                fig_art_qty = px.bar(art_qty, x='quantity', y='article_display', orientation='h', title="Articles Sold by Quantity (Amount)")
                fig_art_qty.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
                st.plotly_chart(fig_art_qty, use_container_width=True)
                
            with c6:
                # Article Sales by Revenue
                art_rev = filtered_df.groupby('article_display')['sales_amount'].sum().reset_index().sort_values('sales_amount', ascending=False)
                fig_art_rev = px.bar(art_rev, x='sales_amount', y='article_display', orientation='h', title="Articles Sold by Revenue (SEK)")
                fig_art_rev.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
                st.plotly_chart(fig_art_rev, use_container_width=True)

# --- TAB 3: AI ANALYSIS ---
with tab3:
    st.header("AI Analysis & Trends")
    from ai_service import AIService # Lazy import
    from database import save_setting, get_setting, delete_setting
    
    # Provider Selection
    provider = st.radio("Select AI Provider", ["Gemini", "ChatGPT"], horizontal=True)
    provider_key = provider.lower().replace("chatgpt", "openai") # 'gemini' or 'openai'
    db_key_name = f"{provider_key}_api_key"
    
    # Load Key from DB if not in session state or to check persistence
    saved_key = get_setting(db_key_name)
    
    # Initialize session state for the key if needed
    if db_key_name not in st.session_state:
        st.session_state[db_key_name] = saved_key if saved_key else ""

    # Display API Key Input
    with st.expander(f"⚙️ {provider} Settings", expanded=not bool(st.session_state[db_key_name])):
        st.markdown(f"""
        To use {provider}, you need an API Key.
        """)
        
        # Input field
        api_key_input = st.text_input(f"Enter {provider} API Key", value=st.session_state[db_key_name], type="password")
        
        col_save, col_del = st.columns([1, 1])
        with col_save:
            if st.button("Save Key"):
                save_setting(db_key_name, api_key_input)
                st.session_state[db_key_name] = api_key_input
                st.success("API Key saved!")
                st.rerun()
                
        with col_del:
            if st.button("Delete Key", type="primary"):
                delete_setting(db_key_name)
                st.session_state[db_key_name] = ""
                st.success("API Key deleted!")
                st.rerun()

    # Initialize Service
    # Use the key from input (which mirrors session state)
    current_key = st.session_state[db_key_name]
    ai_service = AIService(api_key=current_key, provider=provider_key)
    
    # Simple pass-through for now, using the same data
    if df.empty:
        st.warning("No data.")
    else:
        st.write("Select specific subsets of data to analyze or predict.")
        
        # Selection logic similar to dashboard but simplified
        col1, col2, col3 = st.columns(3)
        with col1:
             # Customer Type
             customer_types_ai = ['All', 'Business', 'Private']
             selected_cust_type_ai = st.selectbox("Focus on Customer Type", customer_types_ai, key='ai_cust_type')
        
        with col2:
             # Specific Customer
             all_customers_ai = ['All'] + sorted(df['customer'].dropna().unique().tolist())
             selected_customer_ai = st.selectbox("Focus on Customer", all_customers_ai, key='ai_cust_specific')
             
        with col3:
             # Article
             all_articles_ai = ['All'] + sorted(df['article_display'].dropna().unique().tolist())
             selected_article_ai = st.selectbox("Focus on Article", all_articles_ai, key='ai_article')
             
        # Filter context for AI
        mask = pd.Series([True] * len(df))
        context_parts = []
        
        if selected_cust_type_ai != 'All':
            is_private = df['customer_number'].astype(str).str.strip().str.startswith('90')
            if selected_cust_type_ai == 'Private':
                mask = mask & is_private
                context_parts.append("Customer Type: Private")
            else:
                mask = mask & (~is_private)
                context_parts.append("Customer Type: Business")
                
        if selected_customer_ai != 'All':
            mask = mask & (df['customer'] == selected_customer_ai)
            context_parts.append(f"Customer: {selected_customer_ai}")
            
        if selected_article_ai != 'All':
            mask = mask & (df['article_display'] == selected_article_ai)
            context_parts.append(f"Article: {selected_article_ai}")
            
        context_str = ", ".join(context_parts) if context_parts else "All Data"
            
        filtered_ai_df = df[mask]
        
        st.divider()
        
        if filtered_ai_df.empty:
            st.warning("No data matches the selection.")
        else:
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                st.subheader("AI Insights")
                if st.button("Analyze Data with AI"):
                    with st.spinner("Generating AI Analysis..."):
                        # Adapt DataFrame for the AI service expectation
                        # No rename needed as service handles 'sales_amount'
                        ai_df = filtered_ai_df.copy()
                        analysis = ai_service.analyze_data(ai_df, context=context_str)
                        st.markdown(analysis)
                        
            with col_btn2:
                st.subheader("Trend Prediction")
                if st.button("Predict Future Trend"):
                    with st.spinner("Calculating Prediction..."):
                         # Adapt DataFrame for the AI service expectation
                        trend_input_df = filtered_ai_df.copy()
                        trend_df = ai_service.predict_trend(trend_input_df)
                        if not trend_df.empty:
                            # Detect which column holds the value (sales_amount or total_amount)
                            y_col = 'sales_amount' if 'sales_amount' in trend_df.columns else 'total_amount'
                            
                            fig_trend = px.line(trend_df, x='date', y=y_col, color='type', 
                                              title=f"Sales Prediction (Next 6 Months) - {context_str}",
                                              color_discrete_map={"Historical": "blue", "Predicted": "orange"})
                            st.plotly_chart(fig_trend, use_container_width=True)
                        else:
                            st.error("Not enough data points to predict trend (need at least 2 days of data).")
