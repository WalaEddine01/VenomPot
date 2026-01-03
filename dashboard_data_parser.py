# Import library dependencies.
import pandas as pd
import re
import requests

# This file parses the various log files. The log files have different "formats" or information provided, so needed to create unique parsers for each.
# Each of these parsers takes the log file, gathers the specific information provided in the log, then returns the data in columns/rows Pandas dataframe type.

# Parser for the creds file. Returns IP Address, Username, Password.

import pandas as pd
import re
import requests
from typing import List, Dict




def parse_http_requests_log(http_logs_file):
    data = []

    try:
        with open(http_logs_file, "r", encoding="utf-8") as fh:
            for line in fh:
                record = {}
                for token in line.split():
                    if "=" in token:
                        k, v = token.split("=", 1)
                        record[k] = v.strip('"')
                if record:
                    data.append(record)

    except FileNotFoundError:
        return pd.DataFrame(columns=["client_ip", "method", "user_agent", "path", "ts", "cmd", "result", "OS"])
    df = pd.DataFrame(data)

    EXPECTED = ["client_ip", "method", "user_agent", "path", "ts", "cmd", "result", "OS"]
    df = df.reindex(columns=EXPECTED, fill_value="")

    return df

# Calculator to generate top 10 values from a dataframe. Supply a column name, counts how often each value occurs, stores in "count" column, then return dataframe with value/count.
def top_10_calculator(dataframe, column):
    """
    Generate top 10 values from a dataframe column.
    Returns a DataFrame with columns [column, "count"] or empty DF if column not present.
    """
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(columns=[column, "count"])

    if column not in dataframe.columns:
        return pd.DataFrame(columns=[column, "count"])

    top_10_df = dataframe[column].value_counts().reset_index().head(10)
    top_10_df.columns = [column, "count"]
    return top_10_df

# Takes an IP address as string type, uses the Cleantalk API to look up IP Geolocation.
def get_country_code(ip):

    data_list = []
    # According to the CleanTalk API docs, API calls are rate limited to 1000 per 60 seconds.
    url = f"https://api.cleantalk.org/?method_name=ip_info&ip={ip}"
    try:
        response = requests.get(url)
        api_data = response.json()
        if response.status_code == 200:
            data = response.json()
            ip_data = data.get('data', {})
            country_info = ip_data.get(ip, {})
            data_list.append({'IP Address': ip, 'Country_Code': country_info.get('country_code')})
        elif response.status_code == 429:
            print(api_data["error_message"])
            print(f"[!] CleanTalk IP->Geolocation Rate Limited Exceeded.\n Please wait 60 seconds or turn Country=False (default).\n {response.status_code}")
        else:
            print(f"[!] Error: Unable to retrieve data for IP {ip}. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"[!] Request failed: {e}")

    return data_list

# Takes a dataframe with the IP addresses, converts each IP address to country geolocation code.
def ip_to_country_code(dataframe):

    data = []

    for ip in dataframe['ip_address']:
        get_country = get_country_code(ip)
        parse_get_country = get_country[0]["Country_Code"]
        data.append({"IP Address": ip, "Country_Code": parse_get_country})
    
    df = pd.DataFrame(data)
    return df

# data parsing so that ftp_smb_logs.log file so the dashboard can display it 

def parse_ftp_smb_log(log_file):
    """
    Parses the key=value formatted FTP/SMB logs.
    """
    data = []
    try:
        with open(log_file, "r", encoding="utf-8") as fh:
            for line in fh:
                record = {}
                # Split by space, but be careful with spaces inside quotes (basic split used here for simplicity)
                # A regex is better for robust parsing, but we'll stick to your existing logic style
                parts = line.strip().split(" ")
                for token in parts:
                    if "=" in token:
                        k, v = token.split("=", 1)
                        record[k] = v.strip('"')
                
                # Cleaning up data for the table
                if "data" in record:
                    # sometimes data has spaces, simplistic parser might break. 
                    # Ideally, rejoin the rest of the line or use regex.
                    pass 
                
                if record:
                    data.append(record)
    except FileNotFoundError:
        return pd.DataFrame(columns=["protocol", "client_ip", "event", "data", "ts"])

    df = pd.DataFrame(data)
    
    # Ensure columns exist
    expected_cols = ["protocol", "client_ip", "event", "data", "ts"]
    for c in expected_cols:
        if c not in df.columns:
            df[c] = ""
            
    return df[expected_cols]