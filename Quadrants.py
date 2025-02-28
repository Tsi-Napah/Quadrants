import pandas as pd
import pandas_datareader.data as web
import matplotlib.pyplot as plt
import datetime
import sys
import subprocess

# Constants
TWO_YEAR_SHIFT = 24
TEN_YEAR_SHIFT = 120
SEVEN_YEAR_DAYS = '2555D'

def open_image(path):
    image_viewer = {
        'linux': 'xdg-open',
        'win32': 'explorer',
        'darwin': 'open'
    }.get(sys.platform)
    if image_viewer:
        subprocess.Popen([image_viewer, path])

def save_and_open_image(filename):
    plt.savefig(filename)
    open_image(filename)

################# Money ###################

# Download CPI data from FRED
start_date = datetime.datetime(1990, 1, 1)
end_date = datetime.datetime.now()
end_date_str = end_date.strftime("%d-%m-%Y")
df = web.DataReader('CPIAUCSL', 'fred', start_date, end_date)

# Calculate annualized inflation rates
df['2y_inflation'] = ((df['CPIAUCSL'] / df['CPIAUCSL'].shift(TWO_YEAR_SHIFT)) ** (1/2) - 1) * 100
df['10y_inflation'] = ((df['CPIAUCSL'] / df['CPIAUCSL'].shift(TEN_YEAR_SHIFT)) ** (1/10) - 1) * 100

# Resample to annual frequency (end of year)
annual_df = df.resample('YE').last()

# Calculate rate of change (annual differences)
annual_df['2y_roc'] = annual_df['2y_inflation'].diff()
annual_df['10y_roc'] = annual_df['10y_inflation'].diff()

# Calculate the difference in rate of change
annual_df['roc_diff'] = annual_df['2y_roc'] - annual_df['10y_roc']

# Shift the difference to the start of the year for alignment with background shading
annual_df_shifted = annual_df.copy()
annual_df_shifted.index = annual_df_shifted.index - pd.DateOffset(years=1)

# Identify periods where 2-year acceleration exceeds 10-year
inflation = annual_df['2y_roc'] > annual_df['10y_roc']
deflation = annual_df['2y_roc'] < annual_df['10y_roc']

# Create plot
plt.figure(figsize=(12, 6))
plt.plot(annual_df.index, annual_df['2y_inflation'], label='2-Year Inflation Rate', color='blue')
plt.plot(annual_df.index, annual_df['10y_inflation'], label='10-Year Inflation Rate', color='green')
plt.step(annual_df_shifted.index, annual_df_shifted['roc_diff'], label='Difference in Rate of Change (Shifted)', color='grey', linestyle='--', where='post')
plt.axhline(y=0, color='grey', linestyle='--')

# Highlight periods where 2-year grows faster
for year in annual_df[inflation].index:
    start_shade = year.replace(month=1, day=1)
    end_shade = (year + pd.DateOffset(years=1)).replace(month=1, day=1)
    plt.axvspan(start_shade, end_shade, color='yellow', alpha=0.3)
    if year - pd.DateOffset(years=1) not in annual_df[inflation].index:
        plt.text(start_shade, 0.5, start_shade.strftime("%Y"), rotation=90)
    if year + pd.DateOffset(years=1) not in annual_df[inflation].index:
        plt.text(end_shade, 0.5, end_shade.strftime("%Y"), rotation=90)

plt.title(f'2-Year vs. 10-Year Annualized Inflation Rates\nyellow=inflation, actual difference: {annual_df["roc_diff"].iloc[-1]:.3g}')
plt.ylabel('Inflation Rate (%) / Difference')
plt.xlabel('Year')
plt.legend()
plt.grid(True)

save_and_open_image(f"inflation-{end_date_str}.png")

################### Economy ###################

# Fetch data from FRED
sp500 = web.DataReader('SP500', 'fred', start_date, end_date)
cl1 = web.DataReader('DCOILWTICO', 'fred', start_date, end_date)  # WTI Crude Oil Price

# Merge datasets and clean
df = pd.concat([sp500, cl1], axis=1)
df.columns = ['SP500', 'CL1']
df = df.dropna()

# Calculate ratio and moving average
df['Ratio'] = df['SP500'] / df['CL1']
df['MA_7Y'] = df['Ratio'].rolling(window=SEVEN_YEAR_DAYS, min_periods=1).mean()  # 7-year moving average

#last distance ratio to 7ma
df['economy'] = df['Ratio'] - df['MA_7Y']

# Create plot
plt.figure(figsize=(14, 8))
plt.title(f'SP500/CL1 Ratio with 7-Year Moving Average\nactuel: {df["economy"].iloc[-1]:.3g}', fontsize=16)
plt.xlabel('Date', fontsize=12)
plt.ylabel('Ratio', fontsize=12)

# Plot main series
plt.plot(df.index, df['Ratio'], label='SP500/CL1 Ratio', linewidth=1.5)
plt.plot(df.index, df['MA_7Y'], label='7-Year Moving Average', linestyle='--', linewidth=1.5)

# Shade areas where ratio is above MA
plt.fill_between(df.index, df['Ratio'], df['MA_7Y'], where=(df['Ratio'] >= df['MA_7Y']), facecolor='green', alpha=0.3, interpolate=True)
plt.fill_between(df.index, df['Ratio'], df['MA_7Y'], where=(df['Ratio'] < df['MA_7Y']), facecolor='red', alpha=0.3, interpolate=True)

plt.legend(loc='upper left', fontsize=12)
plt.grid(True, which='both', linestyle='--', alpha=0.7)
plt.tight_layout()
#plt.show()

save_and_open_image(f"growth-{end_date_str}.png")

################# 4 quadrants ###################

# Align the data frequencies by resampling economy data to annual
economy_annual = df['economy'].resample('YE').last()

# Create a combined dataframe
combined_df = pd.DataFrame({
    'money': annual_df['roc_diff'],
    'economy': economy_annual,
    'date': annual_df.index
}).dropna()

combined_df

plt.figure(figsize=(10, 8))
scatter = plt.scatter(combined_df['economy'], combined_df['money'], color="black", alpha=0.7, edgecolors='w', linewidths=0.5)

for year in combined_df.index:
    row = combined_df.loc[f'{year}']
    money_value = row['money']
    economy_value = row['economy']
    plt.annotate(str(year.year), (economy_value, money_value))
                        
plt.plot(combined_df['economy'], combined_df['money'], color='grey', linestyle='--')                     

# Add quadrant lines
plt.axhline(0, color='black', linestyle='--', linewidth=1.8)
plt.axvline(0, color='black', linestyle='--', linewidth=1.8)

# Add labels and title
plt.title('Money vs Economy')
plt.xlabel('Economy (SP500/Oil vs 7Y MA)')
plt.ylabel('Money (2Y-10Y Inflation Acceleration)')
plt.grid(True)

# Highlight latest point
latest_point = combined_df.iloc[-1]
plt.scatter(latest_point['economy'], latest_point['money'], color='red', s=100)

plt.tight_layout()
save_and_open_image(f"quadrants-{end_date_str}.png")
