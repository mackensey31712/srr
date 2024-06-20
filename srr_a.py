import streamlit as st
import pandas as pd
import time
import numpy as np
import altair as alt
from streamlit_lottie import st_lottie
import requests
import json
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode
import plotly.express as px
import hmac
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="SRR Agent View", page_icon=":mag_right:", layout="wide")

#  Access usernames and passwords from secrets.toml
credentials = st.secrets["credentials"]

def login_form():
    """Form with widgets to collect user information"""
    with st.form("Credentials"):
        username_input = st.text_input("Username", key="username_input")
        password_input = st.text_input("Password", type="password", key="password_input")
        submit_button = st.form_submit_button("Log in")

        if submit_button:
            if username_input in credentials and credentials[username_input] == password_input:
                st.session_state.user_auth = True
                st.session_state.username = username_input
                st.session_state["password"] = password_input
                st.rerun()
                
            else:
                st.error("😕 User not known or password incorrect")
                

def logout_button():
    if st.sidebar.button("Log Out"):
        st.session_state.user_auth = False
        st.session_state.username = ""
        st.rerun()



def main():
    if 'user_auth' not in st.session_state:
        st.session_state.user_auth = False
    if 'username' not in st.session_state:
        st.session_state.username = ""

    if not st.session_state.user_auth:
        login_form()
    else:
        logout_button()

        # Create functions for computation
        # @st.cache_data(ttl=120, show_spinner=True)
        # def load_data(url):
        #     df = pd.read_csv(url)
        #     df['Date Created'] = pd.to_datetime(df['Date Created'], errors='coerce')  # set 'Date Created' as datetime
        #     df.rename(columns={'In process (On It SME)': 'SME (On It)'}, inplace=True)  # Renaming column
        #     df['TimeTo: On It (Raw)'] = df['TimeTo: On It'].copy()
        #     df['TimeTo: Attended (Raw)'] = df['TimeTo: Attended'].copy()
        #     df.drop('Survey', axis=1, inplace=True)
        #     return df
        # Set timezone to America/Los_Angeles
    timezone = pytz.timezone('America/Los_Angeles')

    @st.cache_data(ttl=120, show_spinner=True)
    def load_data(data):
        df = data.copy()  # Make a copy to avoid modifying the original DataFrame
        df['Date Created'] = pd.to_datetime(df['Date Created'], errors='coerce').dt.tz_localize(timezone)
        df.rename(columns={'In process (On It SME)': 'SME (On It)'}, inplace=True)
        df['TimeTo: On It (Raw)'] = df['TimeTo: On It'].copy()
        df['TimeTo: Attended (Raw)'] = df['TimeTo: Attended'].copy()
        df.drop('Survey', axis=1, inplace=True)
        df.dropna(subset=['Service'], inplace=True)
        return df

    def calculate_metrics(df):
        unique_case_count = df['Service'].count()
        return unique_case_count

    def convert_to_seconds(time_str):
        if pd.isnull(time_str):
            return 0
        try:
            h, m, s = map(int, time_str.split(':'))
            return h * 3600 + m * 60 + s
        except ValueError:
            return 0

    def seconds_to_hms(seconds):
        if np.isnan(seconds):
            return "00:00:00"
        sign = "-" if seconds < 0 else ""
        seconds = abs(seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"

    def minutes_to_hms(minutes):
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        secs = 0
        return f"{hours:02d}:{mins:02d}:{secs:02d}"

    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Response and Survey Form", usecols=list(range(31)))
    df = load_data(data).copy()

    def load_lottieurl(url: str):
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()

    lottie_globe = load_lottieurl("https://lottie.host/1df5f62e-c32f-47e8-aece-793c034b27e9/sQMtFYb9Rm.json")
    lottie_clap = load_lottieurl("https://lottie.host/af0a6ccc-a8ac-4921-8564-5769d8e09d1e/4Czx1gna6U.json")
    lottie_queuing = load_lottieurl("https://lottie.host/910429d2-a0a4-4668-a4d4-ee831f9ccecd/yOKbdL2Yze.json")
    lottie_inprogress = load_lottieurl("https://lottie.host/c5c6caea-922b-4b4e-b34a-41ecaafe2a13/mphMkSfOkR.json")
    lottie_chill = load_lottieurl("https://lottie.host/2acdde4d-32d7-44a8-aa64-03e1aa191466/8EG5a8ToOQ.json")

    col1, col2 = st.columns([3, .350])
    with col2:
        if st.button('Refresh Data'):
            st.cache_data.clear()
            st.rerun()

    st.markdown(
        f"<h1 style='text-align: center;'>Five9 SRR Agent View</h1>",
        unsafe_allow_html=True
    )

    st_lottie(lottie_globe, speed=1, reverse=False, loop=True, quality="low", height=200, width=200, key=None)

    five9logo_url = "https://raw.githubusercontent.com/mackensey31712/srr/main/five9log1.png"
    st.sidebar.image(five9logo_url, width=200)

    st.sidebar.markdown('# Select a **Filter:**')

    with st.sidebar:
        all_services_options = ['All'] + list(df['Service'].unique())
        selected_service = st.multiselect('Service - (Multi-Select)', all_services_options, default='All')

    if 'All' in selected_service:
        df_filtered = df
    elif not selected_service:
        st.sidebar.markdown("<h3 style='color: red;'>Displaying All Services</h1>", unsafe_allow_html=True)
        df_filtered = df
    else:
        df_filtered = df[df['Service'].isin(selected_service)]

    with st.sidebar:
        selected_month = st.selectbox('Month', ['All'] + list(df_filtered['Month'].unique()))

    if selected_month != 'All':
        df_filtered = df_filtered[df_filtered['Month'] == selected_month]

    with st.sidebar:
        selected_weekend = st.selectbox('Weekend?', ['All', 'Yes', 'No'])

    if selected_weekend != 'All':
        df_filtered = df_filtered[df_filtered['Weekend?'] == selected_weekend]

    with st.sidebar:
        selected_working_hours = st.selectbox('Working Hours?', ['All', 'Yes', 'No'])

    if selected_working_hours != 'All':
        df_filtered = df_filtered[df_filtered['Working Hours?'] == selected_working_hours]

    with st.sidebar:
        all_sme_options = ['All'] + list(df_filtered['SME (On It)'].unique())
        selected_sme_on_it = st.multiselect('SME (On It) - (Multi-Select)', all_sme_options, default='All')

    if 'All' in selected_sme_on_it:
        st.sidebar.markdown("---")
    elif not selected_sme_on_it:
        st.sidebar.markdown("<h3 style='color: red;'>Displaying All SMEs</h1>", unsafe_allow_html=True)
    else:
        df_filtered = df_filtered[df_filtered['SME (On It)'].isin(selected_sme_on_it)]
        st.sidebar.markdown("<h3 style='color: red;'>Displaying Selected SMEs</h1>", unsafe_allow_html=True)

    df_inqueue = df_filtered[df_filtered['Status'] == 'In Queue']
    df_inqueue = df_inqueue[['Case #', 'Requestor', 'Service', 'Creation Timestamp', 'Message Link']]
    df_inprogress = df_filtered[df_filtered['Status'] == 'In Progress']
    df_inprogress = df_inprogress[['Case #', 'Requestor', 'Service', 'Creation Timestamp', 'SME (On It)', 'TimeTo: On It', 'Message Link']]

    df_filtered['TimeTo: On It Sec'] = df_filtered['TimeTo: On It'].apply(convert_to_seconds)
    df_filtered['TimeTo: Attended Sec'] = df_filtered['TimeTo: Attended'].apply(convert_to_seconds)

    df_filtered['TimeTo: On It'] = pd.to_timedelta(df_filtered['TimeTo: On It'])
    df_filtered['TimeTo: Attended'] = pd.to_timedelta(df_filtered['TimeTo: Attended'])

    overall_avg_on_it_sec = df_filtered['TimeTo: On It'].dt.total_seconds().mean()
    overall_avg_attended_sec = df_filtered['TimeTo: Attended'].dt.total_seconds().mean()

    overall_avg_on_it_hms = seconds_to_hms(overall_avg_on_it_sec)
    overall_avg_attended_hms = seconds_to_hms(overall_avg_attended_sec)
    unique_case_count = calculate_metrics(df_filtered)

    col1, col3, col5 = st.columns(3)
    with col1:
        st.metric(label="Interactions", value=unique_case_count)
    with col3:
        st.metric("Overall Avg. TimeTo: On It", overall_avg_on_it_hms)
    with col5:
        st.metric("Overall Avg. TimeTo: Attended", overall_avg_attended_hms)

    df_inqueue['Case #'] = df_inqueue['Case #'].astype(str).str.replace(',', '')
    df_inprogress['Case #'] = df_inprogress['Case #'].astype(str).str.replace(',', '')

    in_queue_count = len(df_inqueue)

    if in_queue_count == 0:
        col1, col2 = st.columns([0.3, 1.2])
        with col1:
            st.title(f'In Queue (0)')
        with col2:
            st_lottie(lottie_clap, speed=1, height=100, width=200)
        with st.expander("Show Data", expanded=False):
            st.dataframe(df_inqueue, use_container_width=True)
    else:
        col1, col2 = st.columns([0.3, 1.2])
        with col1:
            st.title(f'In Queue ({in_queue_count})')
        with col2:
            st_lottie(lottie_queuing, speed=1, height=100, width=200)
        with st.expander("Show Data", expanded=False):
            df_inqueue_display = df_inqueue.reset_index(drop=True)
            df_inqueue_display.index = df_inqueue_display.index + 1
            st.dataframe(df_inqueue_display, use_container_width=True)

    in_progress_count = len(df_inprogress)
    if in_progress_count == 0:
        col1, col2 = st.columns([0.4, 1.2])
        with col1:
            st.title(f'In Progress (0)')
        with col2:
            st_lottie(lottie_chill, speed=1, height=100, width=200)
        with st.expander("Show Data", expanded=False):
            st.dataframe(df_inprogress, use_container_width=True)
    else:
        col1, col2 = st.columns([0.4, 1.2])
        with col1:
            st.title(f'In Progress ({in_progress_count})')
        with col2:
            st.lottie(lottie_inprogress, speed=1, height=100, width=200)
        with st.expander("Show Data", expanded=False):
            df_inprogress_display = df_inprogress.reset_index(drop=True)
            df_inprogress_display.index = df_inprogress_display.index + 1
            st.dataframe(df_inprogress_display, use_container_width=True)

    filtered_columns = ['Case #', 'Service', 'Inquiry', 'Requestor', 'Creation Timestamp',
        'SME (On It)', 'On It Time', 'Attendee', 'Attended Timestamp',
        'Message Link', 'Message Link 0', 'Message Link 1', 'Message Link 2',
        'Status', 'Case Reason', 'AFI', 'AFI Comment', 'Article#',
        'TimeTo: On It (Raw)', 'TimeTo: Attended (Raw)','Month', 'Day', 'Weekend?',
        'Date Created', 'Working Hours?', 'Hour_Created']

    # Display the filtered dataframe
    st.title('Data')
    with st.expander('Show Data', expanded=False):
        df_display = df_filtered[filtered_columns].copy()
        df_display.index = df_display.index + 1  # Adjust the index to start from 1
        st.dataframe(df_display, use_container_width=True)

    agg_month = df_filtered.groupby('Month').agg({
        'TimeTo: On It Sec': 'mean',
        'TimeTo: Attended Sec': 'mean'
    }).reset_index()

    agg_month['TimeTo: On It'] = agg_month['TimeTo: On It Sec'].apply(seconds_to_hms)
    agg_month['TimeTo: Attended'] = agg_month['TimeTo: Attended Sec'].apply(seconds_to_hms)

    agg_service = df_filtered.groupby('Service').agg({
        'TimeTo: On It Sec': 'mean',
        'TimeTo: Attended Sec': 'mean'
    }).reset_index()

    agg_service['TimeTo: On It'] = agg_service['TimeTo: On It Sec'].apply(seconds_to_hms)
    agg_service['TimeTo: Attended'] = agg_service['TimeTo: Attended Sec'].apply(seconds_to_hms)

    agg_month['TimeTo: On It Minutes'] = agg_month['TimeTo: On It Sec'] / 60
    agg_month['TimeTo: Attended Minutes'] = agg_month['TimeTo: Attended Sec'] / 60

    col1, col5 = st.columns(2)

    agg_month.rename(columns={
        'TimeTo: On It Minutes': 'TimeTo_On_It_Minutes',
        'TimeTo: Attended Minutes': 'TimeTo_Attended_Minutes'
    }, inplace=True)

    agg_month_long = agg_month.melt(id_vars=['Month'],
                                    value_vars=['TimeTo_On_It_Minutes', 'TimeTo_Attended_Minutes'],
                                    var_name='Category',
                                    value_name='Minutes')

    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

    chart = alt.Chart(agg_month_long).mark_bar().encode(
        x=alt.X('Month', sort=month_order),
        y=alt.Y('Minutes', stack='zero'),
        color='Category',
        tooltip=['Month', 'Category', 'Minutes']
    ).properties(
        title='Monthly Response Times',
        width=800,
        height=600
    )

    agg_month['TimeTo_On_It_HH:MM:SS'] = agg_month['TimeTo_On_It_Minutes'].apply(minutes_to_hms)
    agg_month['TimeTo_Attended_HH:MM:SS'] = agg_month['TimeTo_Attended_Minutes'].apply(minutes_to_hms)

    csv = agg_month.to_csv(index=False).encode('utf-8')

    with col1:
        st.write(chart)
        with st.expander(':blue[Show Data]', expanded=False):
            agg_month_filtered = agg_month[agg_month['Month'].isin(month_order)]
            agg_month_filtered['Month'] = pd.Categorical(agg_month_filtered['Month'], categories=month_order, ordered=True)
            agg_month_sorted = agg_month_filtered.sort_values('Month').reset_index(drop=True)
            agg_month_sorted.index = agg_month_sorted.index + 1
            st.dataframe(agg_month_sorted[['Month', 'TimeTo_On_It_HH:MM:SS', 'TimeTo_Attended_HH:MM:SS']], use_container_width=True)
            csv = agg_month_sorted[['Month', 'TimeTo_On_It_HH:MM:SS', 'TimeTo_Attended_HH:MM:SS']].to_csv(index=False).encode('utf-8')
            st.download_button(':green[Download Data]', csv, file_name='monthly_response_times.csv', mime='text/csv', help="Click to download the Monthly Response Times in CSV format")

    agg_service['TimeTo_On_It_Minutes'] = agg_service['TimeTo: On It Sec'] / 60
    agg_service['TimeTo_Attended_Minutes'] = agg_service['TimeTo: Attended Sec'] / 60

    agg_service_long = agg_service.melt(id_vars=['Service'],
                                        value_vars=['TimeTo_On_It_Minutes', 'TimeTo_Attended_Minutes'],
                                        var_name='Category',
                                        value_name='Minutes')

    chart2 = alt.Chart(agg_service_long).mark_bar().encode(
        x='Service',
        y=alt.Y('Minutes', stack='zero'),
        color='Category',
        tooltip=['Service', 'Category', 'Minutes']
    ).properties(
        title='Group Response Times',
        width=800,
        height=600
    )

    with col5:
        st.write(chart2)
        agg_service['TimeTo_On_It_HH:MM:SS'] = agg_service['TimeTo_On_It_Minutes'].apply(minutes_to_hms)
        agg_service['TimeTo_Attended_HH:MM:SS'] = agg_service['TimeTo_Attended_Minutes'].apply(minutes_to_hms)
        with st.expander(':blue[Show Data]', expanded=False):
            agg_service_display = agg_service[['Service', 'TimeTo_On_It_HH:MM:SS', 'TimeTo_Attended_HH:MM:SS']].reset_index(drop=True)
            agg_service_display.index = agg_service_display.index + 1
            st.dataframe(agg_service_display, use_container_width=True)
            csv = agg_service_display.to_csv(index=False).encode('utf-8')
            st.download_button(':green[Download Data]', csv, file_name='group_response_times.csv', mime='text/csv', help="Click to download the Group Response Times in CSV format")

    service_counts = df_filtered['Service'].value_counts().reset_index()
    service_counts.columns = ['Service', 'Count']

    chart3 = px.bar(service_counts, x='Service', y='Count', color='Service', text='Count', title='Interaction Count')
    chart3.update_traces(textposition='outside')
    chart3.update_layout(uniformtext_minsize=8, uniformtext_mode='hide', xaxis_tickangle=-0)
    chart3.update_layout(width=800, height=600)

    with col1:
        st.write(chart3)

    chart4 = alt.Chart(df_filtered[df_filtered['SME'].notna()]).mark_bar().encode(
        y=alt.Y('SME:N', sort='-x'),
        x=alt.X('count()', title='Unique Case Count'),
        tooltip=['SME', 'count()']
    ).properties(
        title='Interactions Handled by SME Attended',
        width=700,
        height=600
    )

    data_chart4 = df_filtered[df_filtered['SME'].notna()]['SME'].value_counts().reset_index()
    data_chart4.index = data_chart4.index + 1
    data_chart4.columns = ['SME', 'Unique Case Count']

    with col5:
        st.write(chart4)
        with st.expander("Show Data", expanded=False):
            st.dataframe(data_chart4, use_container_width=True)

    st.subheader('Interaction Count by Requestor')

    pivot_df = df_filtered.pivot_table(index='Requestor', columns='Service', aggfunc='size', fill_value=0)
    pivot_df.reset_index(inplace=True)

    gb = GridOptionsBuilder.from_dataframe(pivot_df)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)

    gridOptions = gb.build()

    AgGrid(pivot_df, gridOptions=gridOptions, update_mode=GridUpdateMode.MODEL_CHANGED, fit_columns_on_grid_load=True)

    csv = pivot_df.to_csv(index=False).encode('utf-8')
    st.download_button(':green[Download Data]', csv, file_name='interaction_count_by_requestor.csv', mime='text/csv', help="Download Interaction Count by Requestor Data in CSV format")

    df_grouped = df_filtered.groupby('SME (On It)').agg(
        Avg_On_It_Sec=pd.NamedAgg(column='TimeTo: On It Sec', aggfunc='mean'),
        Avg_Attended_Sec=pd.NamedAgg(column='TimeTo: Attended Sec', aggfunc='mean'),
        Number_of_Interactions=pd.NamedAgg(column='SME (On It)', aggfunc='count')
    ).reset_index()

    df_grouped['Total_Avg_Sec'] = df_grouped['Avg_On_It_Sec'] + df_grouped['Avg_Attended_Sec']
    df_sorted = df_grouped.sort_values(by=['Total_Avg_Sec', 'Number_of_Interactions'], ascending=[True, False])
    df_sorted['Avg_On_It'] = df_sorted['Avg_On_It_Sec'].apply(seconds_to_hms)
    df_sorted['Avg_Attended'] = df_sorted['Avg_Attended_Sec'].apply(seconds_to_hms)

    df_sorted.rename(columns={'SME (On It)': 'SME'}, inplace=True)

    st.subheader("SME Summary Table")
    df_sorted_display = df_sorted[['SME', 'Avg_On_It', 'Avg_Attended', 'Number_of_Interactions']].reset_index(drop=True)
    df_sorted_display.index = df_sorted_display.index + 1
    st.dataframe(df_sorted_display, use_container_width=True)

    la_timezone = pytz.timezone('America/Los_Angeles')
    la_now = datetime.now(la_timezone)
    st.sidebar.markdown(f"**Last Updated:** {la_now.strftime('%Y-%m-%d, %H:%M:%S %Z%z')}")

    refresh_rate = 120

    def countdown_timer(duration):
        countdown_seconds = duration

        sidebar_html = st.sidebar.empty()
        sidebar_html.markdown("<p style='color:red;'>Time to refresh: 02:00</p>", unsafe_allow_html=True)

        while countdown_seconds:
            mins, secs = divmod(countdown_seconds, 60)
            timer_text = f"Time to refresh: {mins:02d}:{secs:02d}"
            sidebar_html.markdown(f"<p style='color:red;'>{timer_text}</p>", unsafe_allow_html=True)
            time.sleep(1)
            countdown_seconds -= 1

        sidebar_html.markdown("<p style='color:red;'>Refreshing...</p>", unsafe_allow_html=True)
        st.cache_data.clear()
        st.rerun()

    while True:
        countdown_timer(refresh_rate)

if __name__ == '__main__':
    main()