import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import datetime
import google.generativeai as genai
from openai import OpenAI
import os

import traceback

class AIService:
    def __init__(self, api_key=None, provider='gemini'):
        self.api_key = api_key
        self.provider = provider
        self.model = None
        self.client = None
        
        if api_key:
            self._configure_model(api_key, provider)

    def _configure_model(self, api_key, provider):
        try:
            print(f"Configuring {provider} with key: {api_key[:4]}...{api_key[-4:] if len(api_key)>8 else '****'} length={len(api_key)}")
            if provider == 'gemini':
                genai.configure(api_key=api_key)
                
                # Check available models (optional debug print)
                # models = [m.name for m in genai.list_models()]
                # print(f"Available models: {models}")
                
                self.model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
            elif provider == 'openai':
                self.client = OpenAI(api_key=api_key)
            self.last_error = None
        except Exception as e:
            print(f"Error configuring {provider}: {e}")
            traceback.print_exc()
            self.last_error = f"{str(e)}"
            self.model = None
            self.client = None

    def analyze_data_gemini(self, df, context=""):
        """
        Analyze data using Gemini API.
        """
        if not self.model:
             if not self.api_key:
                 return "⚠️ **API Key Missing**: Please provide a Google Gemini API Key to use this feature."
             # Try to reconfigure if key exists but model is None
             self._configure_model(self.api_key, 'gemini')
             if not self.model:
                 error_msg = self.last_error if hasattr(self, 'last_error') and self.last_error else "Unknown error"
                 return f"⚠️ **Configuration Error**: Could not initialize Gemini model. Details: {error_msg}"
        
        return self._generate_analysis(df, context, self._call_gemini)

    def analyze_data_openai(self, df, context=""):
        """
        Analyze data using OpenAI API.
        """
        if not self.client:
             if not self.api_key:
                 return "⚠️ **API Key Missing**: Please provide an OpenAI API Key to use this feature."
             # Try to reconfigure
             self._configure_model(self.api_key, 'openai')
             if not self.client:
                 return "⚠️ **Configuration Error**: Could not initialize OpenAI client. Check your API Key."

        return self._generate_analysis(df, context, self._call_openai)

    def _call_gemini(self, prompt):
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"⚠️ **Gemini API Error**: {str(e)}"

    def _call_openai(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o", # Or gpt-3.5-turbo depending on preference/cost
                messages=[
                    {"role": "system", "content": "You are a business data analyst."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
             return f"⚠️ **OpenAI API Error**: {str(e)}"

    def _generate_analysis(self, df, context, api_callback):
        if df.empty:
            return "No data available for analysis."

        # Map columns if necessary
        if 'sales_amount' in df.columns:
            amount_col = 'sales_amount'
        elif 'total_amount' in df.columns:
            amount_col = 'total_amount'
        else:
            return "Error: Could not find sales amount column."

        # Prepare summary statistics
        total_sales_val = df[amount_col].sum()
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
        Analyze the following sales data summary and provide strategic insights.
        
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
        2. Identify the most important trends or observations.
        3. Provide 2-3 actionable recommendations to increase profit or sales.
        4. Keep the tone professional but accessible to a small business owner. Format with Markdown.
        """

        return api_callback(prompt)

    def analyze_data(self, df, context=""):
        """
        Dispatch analysis to the configured provider.
        """
        if self.provider == 'gemini':
            return self.analyze_data_gemini(df, context)
        elif self.provider == 'openai':
            return self.analyze_data_openai(df, context)
        else:
            return f"Unknown provider: {self.provider}"
            
    def _mock_analysis(self, df, context):
        """Deprecated mock implementation"""
        return "Mock analysis deprecated. Please use a valid API Key."

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
        
        # Predict next 6 months (approx 180 days)
        last_date = daily_sales['date'].max()
        future_dates = [last_date + datetime.timedelta(days=i) for i in range(1, 181)]
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
