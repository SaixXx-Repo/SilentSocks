import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import datetime
import google.generativeai as genai
import os

class AIService:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.model = None
        if api_key:
            self._configure_model(api_key)

    def _configure_model(self, api_key):
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            print(f"Error configuring Gemini: {e}")
            self.model = None

    def analyze_data_gemini(self, df, context=""):
        """
        Analyze data using Gemini API.
        """
        if not self.model:
             if not self.api_key:
                 return "⚠️ **API Key Missing**: Please provide a Google Gemini API Key to use this feature."
             # Try to reconfigure if key exists but model is None
             self._configure_model(self.api_key)
             if not self.model:
                 return "⚠️ **Configuration Error**: Could not initialize Gemini model. Check your API Key."

        if df.empty:
            return "No data available for analysis."

        # Map columns if necessary
        if 'sales_amount' in df.columns:
            amount_col = 'sales_amount'
        elif 'total_amount' in df.columns:
            amount_col = 'total_amount'
        else:
            return "Error: Could not find sales amount column."

        # Prepare summary statistics for the prompt
        # Explicitly convert to float to avoid Series truth value ambiguity if single-element Series
        # Use .item() if it's a Series, or just cast if scalar. Safest is float(scalar_value) after sum()
        total_sales_val = df[amount_col].sum()
        # Handle case where duplicates exist and sum() returned a Series
        if isinstance(total_sales_val, pd.Series):
             total_sales_val = total_sales_val.iloc[0]
        total_sales = float(total_sales_val)
        
        total_qty_val = df['quantity'].sum() if 'quantity' in df.columns else 0
        if isinstance(total_qty_val, pd.Series):
             total_qty_val = total_qty_val.iloc[0]
        total_qty = int(total_qty_val)
        
        row_count = len(df)
        
        # TB/Profit
        tb_text = ""
        if 'tb_amount' in df.columns:
            total_tb_val = df['tb_amount'].sum()
            if isinstance(total_tb_val, pd.Series):
                total_tb_val = total_tb_val.iloc[0]
            total_tb = float(total_tb_val)
            margin = (total_tb / total_sales * 100) if total_sales > 0 else 0
            tb_text = f"- Total Profit (TB): {total_tb:,.2f} kr (Margin: {margin:.1f}%)\n"
        
        # Top Drivers
        try:
            top_articles = df.groupby('article')[amount_col].sum().sort_values(ascending=False).head(5).to_dict()
            top_customers = df.groupby('customer')[amount_col].sum().sort_values(ascending=False).head(5).to_dict()
        except:
            top_articles = "N/A"
            top_customers = "N/A"
            
        # Trends
        trend_text = "N/A"
        if len(df['date'].unique()) > 1:
            df_sorted = df.sort_values('date')
            first_month = df_sorted.iloc[0]['date']
            last_month = df_sorted.iloc[-1]['date']
            trend_text = f"Data covers period from {first_month} to {last_month}"

        # Construct Prompt
        prompt = f"""
        You are a business data analyst. Analyze the following sales data summary and provide strategic insights.
        
        **Context**: {context}
        
        **Data Summary**:
        - Total Records: {row_count}
        - Total Revenue: {total_sales:,.2f} kr
        {tb_text}- Total Quantity Sold: {total_qty}
        - Period: {trend_text}
        
        **Top 5 Articles (by Revenue)**:
        {top_articles}
        
        **Top 5 Customers (by Revenue)**:
        {top_customers}
        
        **Instructions**:
        1. Summarize the key performance indicators.
        2. Identify the most important trends or observations (e.g., high concentration of sales in specific customers or products).
        3. Provide 2-3 actionable recommendations for the business owner to increase profit or sales.
        4. Keep the tone professional but accessible. Format with Markdown (headers, bullet points).
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"⚠️ **API Error**: {str(e)}"

    def analyze_data(self, df, context=""):
        """
        Legacy mock analysis (fallback if Gemini fails or key not provided).
        """
        # ... (Existing mock logic kept as fallback, but typically we'll use gemini if key is present)
        # For simplicity, if key is present, we try Gemini. If it fails, we return error.
        # If no key, we return the mock message or specific prompt to enter key.
        if self.api_key:
            return self.analyze_data_gemini(df, context)
            
        # Fallback to mock if no key
        return self._mock_analysis(df, context)

    def _mock_analysis(self, df, context):
        """Original mock implementation moved here"""
        if df.empty:
            return "No data available."
            
        # Map columns
        if 'sales_amount' in df.columns:
            amount_col = 'sales_amount'
        elif 'total_amount' in df.columns:
            amount_col = 'total_amount'
        else:
            return "Error: Could not find sales amount column."
            
        total_sales = df[amount_col].sum()
        
        try:
            top_article = df.groupby('article')[amount_col].sum().idxmax()
        except:
            top_article = "N/A"
            
        analysis = (
            f"### AI Analysis Result (Mock)\n\n"
            f"**Note**: Provide a Gemini API Key to get real AI insights.\n\n"
            f"**Context:** {context}\n\n"
            f"Total Revenue: **{total_sales:,.2f}**\n"
            f"Top Article: **{top_article}**"
        )
        return analysis

    def predict_trend(self, df):
        """
        Predict future sales using Linear Regression.
        (Remains unchanged as it uses local sklearn)
        """
        if df.empty:
            return pd.DataFrame()
            
        # Map amount column
        amount_col = 'sales_amount' if 'sales_amount' in df.columns else 'total_amount'
            
        # Aggregate to daily sales
        daily_sales = df.groupby('date')[amount_col].sum().reset_index().sort_values('date')
        
        if len(daily_sales) < 2:
            return pd.DataFrame() # Not enough data for prediction
            
        # Prepare data for regression
        daily_sales['ordinal_date'] = daily_sales['date'].map(datetime.datetime.toordinal)
        
        X = daily_sales[['ordinal_date']]
        y = daily_sales[amount_col]
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict next 30 days
        last_date = daily_sales['date'].max()
        future_dates = [last_date + datetime.timedelta(days=i) for i in range(1, 31)]
        future_ordinals = [[d.toordinal()] for d in future_dates]
        
        future_sales = model.predict(future_ordinals)
        
        # Ensure no negative predictions
        future_sales = [max(0, x) for x in future_sales]
        
        # Create result dataframe
        future_df = pd.DataFrame({
            'date': future_dates,
            amount_col: future_sales,
            'type': 'Predicted'
        })
        
        daily_sales['type'] = 'Historical'
        
        # Combine
        combined_df = pd.concat([daily_sales[['date', amount_col, 'type']], future_df])
        
        return combined_df
