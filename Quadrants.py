import pandas as pd
import numpy as np
import pandas_datareader.data as web
import matplotlib.pyplot as plt
import datetime
import os
import sys
import subprocess

def open_image(path):
    viewer = {'linux': 'xdg-open', 'win32': 'explorer', 'darwin': 'open'}[sys.platform]
    try:
        subprocess.Popen([viewer, path])
    except Exception as e:
        print(f"Error opening image: {e}")

def fetch_data(symbol, start_date, end_date):
    return web.DataReader(symbol, 'fred', start_date, end_date)

def plot_inflation(annual_df, inflation, deflation, end_date, save_dir):
    plt.figure(figsize=(12, 6))
    plt.plot(annual_df.index, annual_df['2y_inflation'], label='2-Year Inflation Rate', color='blue')
    plt.plot(annual_df.index, annual_df['10y_inflation'], label='10-Year Inflation Rate', color='green')
    plt.step(annual_df.index - pd.DateOffset(years=1), annual_df['roc_diff'], label='Rate of Change Difference', color='grey', linestyle='--', where='post')
    plt.axhline(y=0, color='grey', linestyle='--')

        
    # Highlight periods where 2-year grows faster
    for year in annual_df[inflation].index:
        start_shade = year.replace(month=1, day=1)
        end_shade = (year + pd.DateOffset(years=1)).replace(month=1, day=1)
        plt.axvspan(start_shade, end_shade, color='yellow', alpha=0.3)
        if year-pd.DateOffset(years=1) not in annual_df[inflation].index:
            plt.text(start_shade, 0.5, start_shade.strftime("%Y"), rotation=90)
        if year+pd.DateOffset(years=1) not in annual_df[inflation].index:
            plt.text(end_shade, 0.5, end_shade.strftime("%Y"), rotation=90)


    plt.title(f'2-Year vs. 10-Year Annualized Inflation Rates\nYellow = Inflation, Actual Difference: {annual_df["roc_diff"].iloc[-1]:.3g}')
    plt.xlabel('Year')
    plt.ylabel('Inflation Rate (%) / Difference')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    filename = os.path.join(save_dir, f"inflation-{end_date.strftime('%d-%m-%Y')}.png")
    plt.savefig(filename)
    open_image(filename)

def plot_economy(df, end_date, save_dir):
    # Calculate the 7-year moving average and the difference
    df['MA_7Y'] = df['Ratio'].rolling(window='2555D', min_periods=1).mean()
    df['economy'] = df['Ratio'] - df['MA_7Y']

    # Create the plot
    plt.figure(figsize=(14, 8))
    plt.title(f'SP500/CL1 Ratio with 7-Year Moving Average\nActual: {df["economy"].iloc[-1]:.3g}', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Ratio', fontsize=12)

    # Plot the main ratio and moving average
    plt.plot(df.index, df['Ratio'], label='SP500/CL1 Ratio', linewidth=1.5)
    plt.plot(df.index, df['MA_7Y'], label='7-Year Moving Average', linestyle='--', linewidth=1.5)

    # Shade areas where the ratio is above the moving average
    plt.fill_between(df.index, df['Ratio'], df['MA_7Y'], 
                     where=(df['Ratio'] >= df['MA_7Y']), 
                     facecolor='green', alpha=0.3, interpolate=True)

    # Shade areas where the ratio is below the moving average
    plt.fill_between(df.index, df['Ratio'], df['MA_7Y'], 
                     where=(df['Ratio'] < df['MA_7Y']), 
                     facecolor='red', alpha=0.3, interpolate=True)

    # Add the legend
    plt.legend(loc='upper left', fontsize=12)

    # Grid settings
    plt.grid(True, which='both', linestyle='--', alpha=0.7)

    # Tight layout
    plt.tight_layout()

    # Save the plot
    filename = os.path.join(save_dir, f"growth-{end_date.strftime('%d-%m-%Y')}.png")
    plt.savefig(filename)

    # Open the image
    open_image(filename)

def plot_quadrants(combined_df, end_date, save_dir):
    plt.figure(figsize=(10, 8))
    plt.scatter(combined_df['economy'], combined_df['money'], color="black", alpha=0.7, edgecolors='w', linewidths=0.5)

    for year in combined_df.index:
        plt.annotate(str(year.year), (combined_df.loc[year, 'economy'], combined_df.loc[year, 'money']))

    plt.plot(combined_df['economy'], combined_df['money'], color='grey', linestyle='--')
    plt.axhline(0, color='black', linestyle='--', linewidth=1.8)
    plt.axvline(0, color='black', linestyle='--', linewidth=1.8)

    plt.title('Money vs Economy')
    plt.xlabel('Economy (SP500/Oil vs 7Y MA)')
    plt.ylabel('Money (2Y-10Y Inflation Acceleration)')
    plt.grid(True)

    latest_point = combined_df.iloc[-1]
    plt.scatter(latest_point['economy'], latest_point['money'], color='red', s=100)

    plt.tight_layout()
    filename = os.path.join(save_dir, f"quadrants-{end_date.strftime('%d-%m-%Y')}.png")
    plt.savefig(filename)
    open_image(filename)

def main():
    start_date = datetime.datetime(1990, 1, 1)
    end_date = datetime.datetime.now()

    # Create a directory to save images
    save_dir = 'images'
    os.makedirs(save_dir, exist_ok=True)

    # Download data
    df_cpi = fetch_data('CPIAUCSL', start_date, end_date)
    sp500 = fetch_data('SP500', start_date, end_date)
    cl1 = fetch_data('DCOILWTICO', start_date, end_date)

    # Process CPI data for inflation calculations
    df_cpi['2y_inflation'] = ((df_cpi['CPIAUCSL'] / df_cpi['CPIAUCSL'].shift(24)) ** 0.5 - 1) * 100
    df_cpi['10y_inflation'] = ((df_cpi['CPIAUCSL'] / df_cpi['CPIAUCSL'].shift(120)) ** 0.1 - 1) * 100

    # Resample CPI data to annual frequency and calculate rate of change
    annual_df = df_cpi.resample('YE').last()
    annual_df['2y_roc'] = annual_df['2y_inflation'].diff()
    annual_df['10y_roc'] = annual_df['10y_inflation'].diff()
    annual_df['roc_diff'] = annual_df['2y_roc'] - annual_df['10y_roc']

    # Identify inflation and deflation periods
    inflation = annual_df['2y_roc'] > annual_df['10y_roc']
    deflation = annual_df['2y_roc'] < annual_df['10y_roc']

    # Plot inflation data
    plot_inflation(annual_df, inflation, deflation, end_date, save_dir)

    # Process economic data (SP500 and WTI crude oil price)
    df = pd.concat([sp500, cl1], axis=1)
    df.columns = ['SP500', 'CL1']
    df = df.dropna()
    df['Ratio'] = df['SP500'] / df['CL1']

    # Plot economy data
    plot_economy(df, end_date, save_dir)

    # Prepare economy and money data for quadrants
    economy_annual = df['economy'].resample('YE').last()
    combined_df = pd.DataFrame({
        'money': annual_df['roc_diff'],
        'economy': economy_annual,
        'date': annual_df.index
    }).dropna()

    # Plot quadrants
    plot_quadrants(combined_df, end_date, save_dir)

if __name__ == "__main__":
    main()
