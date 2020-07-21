# Import Libraries
import pandas as pd
import requests
import datetime
import json
import tkinter as tk
from tkinter import filedialog

# Intro
print ('This program will take a user portfolio containing ETFs and break it down into exposure to individual holdings')

# Tkinter import GUI
inroot= tk.Tk()
canvas1 = tk.Canvas(inroot, width = 300, height = 300, bg = 'lightgrey', relief = 'raised')
canvas1.pack()

# Get CSV and make new DF of select columns (pf=portfolio)
pf = ()
pft = ()
def getCSV ():

     global pf
     import_file_path = filedialog.askopenfilename()
     data = pd.read_csv(import_file_path)
     # Use line below outside of getCSV if not using tkinter module
     pf = pd.DataFrame(data, columns= ['Symbol','Current Price', 'Purchase Price', 'Quantity'])
     inroot.destroy()

     # Seperate Cdn and US equities by defining str
     cdn1 = '.TO'
     cdn2 = '.V'

     # Define live currency exchange
     r = requests.get('https://api.exchangeratesapi.io/latest?base=USD&symbols=CAD')
     j = r.json()
     x = float(j['rates']['CAD'])

     # US/CAD Current Price calculation
     for i in range(0,len(pf['Current Price'])):
     # I assume here if current price exists then a symbol does as well
     # if .TO is not in symbol OR .V is not in symbol, then
          if not cdn1 in pf.at[i,'Symbol'] or cdn2 in pf.at[i,'Symbol']:
          # update price based on exchange rate
               pf.at[i,'Current Price'] = x * pf.at[i,'Current Price']

     # Calculate total value
     totval = pf['Current Price'] * pf['Quantity']
     pf['Total Value'] = totval

     # Weight of Portfolio calculation
     global pft
     pft= pf['Total Value'].sum()
     wt = pf['Total Value'] / pft 
     pf ['% Assets'] = wt

     # Clean up pf to only include $Ticker and Weights and add a variable for print out before calculating exposure
     del pf['Total Value']
     del pf['Purchase Price']
     del pf['Current Price']
     del pf['Quantity']

     # Clean up user input for print out
     pf1 = pf.sort_values(by = '% Assets', ascending=False)
     valu = pft * pf1['% Assets']
     pf1['Total Value'] = valu
     per = 100 * pf1['% Assets']
     pf1['% Assets'] = per

     pf1['Total Value'] = pf1['Total Value'].round(decimals=2)
     pf1['% Assets'] = pf1['% Assets'].round(decimals=3)

     # Print user input
     print ('This is your current holding exposure: ' , '\n',  pf1)
     print ("Total Portfolio Value: $" + '%.2f' %pft +' CAD')
     print ('Working...')
     
browseButton_CSV = tk.Button(text="      Import CSV from YahooFinance     ", command=getCSV, bg='lightblue', fg='darkblue', font=('impact', 12))
canvas1.create_window(150, 150, window=browseButton_CSV)

inroot.mainloop()
     
# Webscrape
etf_lib = list()
out = pd.DataFrame
def webscrape ():
     global etf_lib
     global out
     global pf
     # Read from yahoofinance for each ticker symbol in user's portfolio
     for i in range(0,len(pf['Symbol'])):
          wds=pd.read_html('https://ca.finance.yahoo.com/quote/%s/holdings?p=%s' 
                         % (pf.at[i, 'Symbol'], pf.at[i, 'Symbol']))
          # Only select webpages which represent an ETF
          if len(wds)==1:
               # Filter col of interest and convert '% Assets' col from str to float
               for wd in wds:
                    for e in range(0,len(wd['% Assets'])):
                         wd.at[e, '% Assets'] = wd.at[e, '% Assets'].replace("%","")
                    wd['% Assets'] = wd['% Assets'].astype(float)
                    # Delete unused data
                    del wd['Name']
                    # Create MISC ticker which represents the % holding of the ETF not accouted for by top 10 holdings
                    etft= 100 - wd['% Assets'].sum()
                    new_row= {'Symbol':(pf.at[i, 'Symbol'] + '_MISC'), '% Assets':etft}
                    wd = wd.append(new_row, ignore_index=True)
                    # Multiply ETF ticker list by weight in portfolio
                    wd['% Assets'] = wd['% Assets'] * pf.at[i, '% Assets']
                    # Append to list of ETF data and remove ETF ticker from list
                    etf_lib.append(wd)
                    pf.drop([i], inplace=True)

     # Concatenate lists together and sum any repeat tickers in list                           
     df = pd.concat(etf_lib) 
     pf['% Assets'] = pf['% Assets'] *100
     df = df.append(pf)
     df = df.groupby(['Symbol'] , as_index=False).sum()
     out = df.sort_values(by = '% Assets', ascending=False)

     # Update and format before print out
     val = pft * (out['% Assets'] / 100)
     out ['Total Value'] = val           
     out['Total Value'] = out['Total Value'].round(decimals=2)
     out['% Assets'] = out['% Assets'].round(decimals=3)

webscrape()

# Tkinter Outport GUI
outroot= tk.Tk()
canvas1 = tk.Canvas(outroot, width = 600, height = 300, bg = 'lightgrey', relief = 'raised')
canvas1.pack()

def exportCSV():
     export_file_path = filedialog.asksaveasfilename(defaultextension='.csv')
     out.to_csv (export_file_path, index = False, header=True)
     outroot.destroy()
     
saveAsButton_CSV = tk.Button(text='Export resulting equitity expsoure to CSV', command=exportCSV, bg='lightblue', fg='darkblue', font=('impact', 12))
canvas1.create_window(300, 150, window=saveAsButton_CSV)

outroot.mainloop()

print ('Complete!')