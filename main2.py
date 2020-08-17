# Import Libraries
import pandas as pd
import requests
import datetime
import json
from bs4 import BeautifulSoup

# Intro
print ('This program will take a user portfolio containing ETFs and break it down into exposure to individual holdings.')

# Take CSV and turn into pandas dataframe
data = pd.read_csv('quotes.csv')

# Get CSV and make new DF of select columns (pf=portfolio)
pf = pd.DataFrame(data, columns= ['Symbol', 'Name', 'Current Price', 'Quantity'])

# Add Name column to DF
for i in range(0,len(pf['Symbol'])):
    # Format symbol column for webscraping
    pf.at[i, 'Symbol'] = pf.at[i, 'Symbol'].replace("-",".")
    # Let soup do its thing
    url = ('https://ycharts.com/companies/%s' % pf.at[i, 'Symbol'])
    get_url = requests.get(url)
    get_text = get_url.text
    soup = BeautifulSoup(get_text, "html.parser")
    try:
        for div in soup.findAll('h1', attrs={'class':'securityName'}):
            name= div.find('a').contents[0]
            print(name)
            pf.Name = pf.Name.fillna('')
            pf.at[i, 'Name'] = name
    except:
        pass
    else:
        for div in soup.findAll('h1', attrs={'class':'index-name-text'}):
            name= div.string
            name = name.replace("\n", "")
            name = name[24:]
            print(name)
            pf.Name = pf.Name.fillna('')
            pf.at[i, 'Name'] = name

# Create dict of ETF names to append to final print out
etfnames = {}
for i in range(0,len(pf['Name'])):
    print(pf.at[i, 'Name'])
    if 'ETF' in pf.at[i, 'Name']:
        etfnames.setdefault(pf.at[i,'Symbol'], pf.at[i,'Name'] )

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
        pf.at[i,'Current Price'] *= x

# Calculate total value
totval = pf['Current Price'] * pf['Quantity']
pf['Total Value'] = totval

# Weight of Portfolio calculation
pft= pf['Total Value'].sum()
wt = pf['Total Value'] / pft 
pf ['% Weight'] = wt

# Clean up pf to only include $Ticker and Weights and add a variable for print out before calculating exposure
del pf['Total Value']
del pf['Current Price']
del pf['Quantity']

# Clean up user input for print out
pf1 = pf.sort_values(by = '% Weight', ascending=False)
valu = pft * pf1['% Weight']
pf1['Total Value'] = valu
per = 100 * pf1['% Weight']
pf1['% Weight'] = per
pf1['Total Value'] = pf1['Total Value'].round(decimals=2)
pf1['% Weight'] = pf1['% Weight'].round(decimals=3)

# Print user input
print ('This is your current holding exposure: ' , '\n',  pf1)
print ("Total Portfolio Value: $" + '%.2f' %pft +' CAD')
print ('Working...')

# Webscrape
etf_lib = list()

# Read from ycharts for each ticker symbol in user's portfolio
for i in range(0,len(pf['Symbol'])):
    try:
        wds=pd.read_html('https://ycharts.com/companies/%s/holdings' % pf.at[i, 'Symbol'])[1]
    # This statement skips equities so the scraper can pull ETF data only
    except:
        pass
    else:
        wds = wds.rename(columns={"%\xa0Weight": "% Weight", "%\xa0Change" : "% Chg"})
        # Filter col of interest and convert '% Assets' col from str to float, format Symbol col
        for j in range(0,len(wds['% Weight'])):
            wds.at[j, '% Weight'] = wds.at[j, '% Weight'].replace("%","")
            wds.at[j, 'Symbol'] = wds.at[j, 'Symbol'].replace("-",".")
        wds['% Weight'] = wds['% Weight'].astype(float)
        # Delete unused data
        del wds['Price']
        del wds['% Chg']
        # Create MISC ticker which represents the % holding of the ETF not accouted for by top 25 holdings
        etft= 100 - wds['% Weight'].sum()
        new_row= {'Symbol':(pf.at[i, 'Symbol']), '% Weight':etft}
        wds = wds.append(new_row, ignore_index=True)
        # Multiply ETF ticker list by weight in portfolio
        wds['% Weight'] = wds['% Weight'] * pf.at[i, '% Weight']
        # Append to list of ETF data and remove ETF ticker from list
        etf_lib.append(wds)
        pf.drop([i], inplace=True)

# Concatenate lists together and sum any repeat tickers in list
df = pd.concat(etf_lib)
pf['% Weight'] *= 100
df = df.append(pf)
# Save names as a dict object with symbols as keys and names as values
names = dict(zip(df['Symbol'], df['Name']))
# This command will combine repeat tickers and sum their values, but doing so deletes the Name col
df = df.groupby(['Symbol'] , as_index=False).sum()
out = df.sort_values(by = '% Weight', ascending=False)

# Add empty Name col to out df and re-index
out["Name"] = ['' for _ in range(len(out))]
columnsTitles = ['Symbol', 'Name', '% Weight', 'Total Value']
out = out.reindex(columns=columnsTitles)

# Correct name column to values saved in names dictionary
for i in range(0,len(out['Symbol'])):
    for j in names.keys():
        if str(j) == str(out.at[i, 'Symbol']):
            out.at[i, 'Name'] = names.get(j)

# Re-add ETF Names
for i in range(0,len(out['Symbol'])):
    for j in etfnames.keys():
        if str(j) in str(out.at[i, 'Symbol']):
            out.at[i, 'Name'] = ('Misc ' + str(etfnames.get(j)) + ' Holdings')

# Update and format before print out
val = pft * (out['% Weight'] / 100)
out ['Total Value'] = val             
out['Total Value'] = out['Total Value'].round(decimals=2)
out['% Weight'] = out['% Weight'].round(decimals=3)

# Output
print ('This is the resulting exposure to individual equities: ' , '\n', out)
out.to_csv('output.csv', index=False)