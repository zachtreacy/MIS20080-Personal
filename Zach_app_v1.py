#%%

#required imports are in requirements.txt

# first set the page configuration as having this code below returned an error
st.set_page_config(page_title="Expected Portfolio Returns", layout="wide")

# now add in dashboard title 
st.title("Expected Portfolio Returns Dashboard")



# now get stock data for chosen portfolio from yfinance
tkr = st.text_input("Enter Stock Ticker", "AAPL").upper() #uppercase tickers to match yfinance format
tkr_data = yf.download([tkr], period = '1y', auto_adjust= True)

#display company name in streamlit app for better UI
tkr_obj = yf.Ticker(tkr)
ticker_info = tkr_obj.info
if ticker_info:
    st.write(f"Company Name: {ticker_info['longName']}")
else:
    st.write("Company Name: Not Found")

#obtaining data from benchmark index (S&P 500)
bm_data = yf.download(["^GSPC"], period = '1y', auto_adjust= True)

#calculating daily returns for both portfolio and benchmark
# portfolio daily returns first:
pf_returns = tkr_data['Close'].pct_change().dropna() 

# benchmark daily returns next:
bm_returns = bm_data['Close'].pct_change().dropna()

#print results to console for verification
print(pf_returns)
print(bm_returns)

# Display results in Streamlit app

# ensure pf_returns and bm_returns are Series (handles DataFrame from yfinance)
#I have a simpler version also but this is needed in order to have sliders in the current version
if isinstance(pf_returns, pd.DataFrame):
    pf_returns = pf_returns.iloc[:, 0].squeeze()
else:
    pf_returns = pf_returns.squeeze()

if isinstance(bm_returns, pd.DataFrame):
    bm_returns = bm_returns.iloc[:, 0].squeeze()
else:
    bm_returns = bm_returns.squeeze()

# interactive sliders and moving average plots (only when data exists)
if pf_returns.empty or bm_returns.empty:
    st.warning("Not enough data to display interactive return charts.")
else:
    # choosing window based on overlapping length so both series have values
    n_max = max(1, min(len(pf_returns), len(bm_returns)))
    show_days = st.slider("Show Last N Days", min_value=1, max_value=365, value= 365)
    ma_window = st.slider("Moving Average Length (Days)", min_value=0, max_value=60, value=0)

    # take tail of each series and align by date
    pf_display = pf_returns.tail(show_days)
    bm_display = bm_returns.tail(show_days)
    df_plot = pd.concat([pf_display.rename(tkr), bm_display.rename("S&P500")], axis=1).dropna()

    # add moving averages if requested
    if ma_window > 0:
        df_plot[f"{tkr}_MA"] = df_plot[tkr].rolling(window=ma_window).mean()
        df_plot["S&P500_MA"] = df_plot["S&P500"].rolling(window=ma_window).mean()

    # portfolio chart
    st.subheader("Portfolio Returns Graph")
    st.write(f"Daily Returns for {tkr} (last {show_days} days):")
    if ma_window > 0:
        st.line_chart(df_plot[[tkr, f"{tkr}_MA"]])
    else:
        st.line_chart(df_plot[[tkr]])

    # benchmark chart
    st.subheader("Benchmark Comparison Graph")
    st.write("Daily Returns for Benchmark (S&P 500):")
    if ma_window > 0:
        st.line_chart(df_plot[["S&P500", "S&P500_MA"]])
    else:
        st.line_chart(df_plot[["S&P500"]])
  


# %% CAPM expected return calculations

Trading_days = 252 # assuming 252 trading days in a year

#add in section subheader into streamlit app
st.subheader("CAPM Expected Returns Analysis")


# allow user to set risk-free rate (annual)
#risk free rate is defaulted to 2% but user can change it betwween 0% and 4%
rf = st.number_input("Choose Annual Risk-Free Rate (Default = 2%)", min_value=0.0, max_value= 0.04, value=0.02, step=0.001, format="%.4f")

# align asset and market returns on overlapping dates
combined = pd.concat([pf_returns, bm_returns], axis=1).dropna()
combined.columns = [tkr, "S&P500"] #tkr is the asset, S&P500 is the market

if combined.empty:
    st.warning("Not enough overlapping returns to compute CAPM. Check data/period.") #warning message if not enough data to avoid crashes
else:
    asset = combined[tkr]
    market = combined['S&P500']

    # Calculate beta as covariance(asset, market) / variance(market)

    beta_cov = np.cov(asset, market)[0, 1] / np.var(market)


    # Have market annual arithmetic return for comparison
    # code for CAGR can be added later if needed

    market_annual_arith = market.mean() * Trading_days


    # CAPM expected return formula is risk free rate + beta * (market return - risk free rate)

    capm_er = rf + beta_cov * (market_annual_arith - rf)


    # Display results in streamlit app
    # beta display is maybe unnecessary but it is useful to see
    #market return is arithmetic
    st.write(f"Estimated Beta: {beta_cov:.4f}")
    st.write(f"Benchmark (S&P 500) Annual Return: {market_annual_arith:.2%}")
    st.write(f"CAPM Annual Expected Return for {tkr}: {capm_er:.2%}")

   # Now calculate realized annual returns for the asset for comparison
   #use both arithmetic and geometric returns
    asset_clean = asset.dropna()
    realized_arith = float(asset_clean.mean() * Trading_days) if len(asset_clean) > 0 else float("nan")
    realized_geom = float((np.prod(1.0 + asset_clean) ** (Trading_days / len(asset_clean))) - 1.0) if len(asset_clean) > 0 else float("nan")

#create dataframe to hold results for display and download
    results_df = pd.DataFrame([{
        "Ticker": tkr,
        "Beta": beta_cov,
        "Benchmark (S&P 500) Annual Return": market_annual_arith,
        "CAPM Portfolio Annual Expected Return": capm_er,
        "Realized Annual Portfolio Arithmetic Return": realized_arith,
        "Realized Annual Portfolio Geometric Return": realized_geom
    }]).set_index("Ticker")

    # UI choice between table and bar chart
    view = st.radio("Show", ["Table", "Bar Chart"], horizontal=True)

    if view == "Table":   # Table view
        st.dataframe(results_df.style.format({
            "Beta": "{:.4f}",
            "Benchmark (S&P 500) Annual Return": "{:.2%}",
            "CAPM Portfolio Annual Expected Return": "{:.2%}",
            "Realized Annual Portfolio Arithmetic Return": "{:.2%}",
            "Realized Annual Portfolio Geometric Return": "{:.2%}"
        }))
    else:  # Bar chart
        
        bar_df = pd.DataFrame({
            "Return Metric": ["CAPM Portfolio Annual Expected Return", "Realized Annual Portfolio Arithmetic Return", "Realized Annual Portfolio Geometric Return"],
            "Annual Percentage Return": [capm_er, realized_geom, realized_arith]
        })
        fig = px.bar(bar_df, x="Return Metric", y="Annual Percentage Return", text=bar_df["Annual Percentage Return"].apply(lambda v: f"{v:.2%}"),
                     title= "CAPM vs Realized Annual Returns Chart")
        fig.update_traces(textposition="outside")
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    # Download results as CSV option (probably not needed for single asset but useful for multiple)
    csv = results_df.reset_index().to_csv(index=False).encode("utf-8")
    st.download_button("Download CAPM Summary CSV", data=csv, file_name=f"{tkr}_capm_summary.csv", mime="text/csv")
    

#still to do:
#-----------------

# needs to be edited at top to account for multiple assets and not just one 
# add in code for equal weighted portfolio calculations
# would like to change colours and layout of dashboard 
# adding in log returns as an option could be useful
#add in more error handling for invalid tickers or no data returned
#add in a doctsring explaining all my variables and functions used



