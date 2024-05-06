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
        @st.cache_data(ttl=120, show_spinner=True)
        def load_data(url):
            df = pd.read_csv(url)
            df['Date Created'] = pd.to_datetime(df['Date Created'], errors='coerce')  # set 'Date Created' as datetime
            df.rename(columns={'In process (On It SME)': 'SME (On It)'}, inplace=True)  # Renaming column
            df['TimeTo: On It (Raw)'] = df['TimeTo: On It'].copy()
            df['TimeTo: Attended (Raw)'] = df['TimeTo: Attended'].copy()
            df.drop('Survey', axis=1, inplace=True)
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
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

        url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSQVnfH-edbXqAXxlCb2FrhxxpsOHJhtqKMYsHWxf5SyLVpAPTSIWQeIGrBAGa16dE4CA59o2wyz59G/pub?gid=0&single=true&output=csv'
        df = load_data(url).copy()

        # Function to load a lottie animation from a URL
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

        # Button to refresh the data - align to upper right
        col1, col2 = st.columns([3, .350])
        with col2:
            if st.button('Refresh Data'):
                # st.experimental_memo.clear()
                st.cache_data.clear()
                # st.experimental_rerun()
                st.rerun()

        # Center align 'five9 srr agent view'
        st.markdown(
            f"<h1 style='text-align: center;'>Five9 SRR Agent View</h1>",
            unsafe_allow_html=True
        )

        # Display lottie animation
        st_lottie(lottie_globe, speed=1, reverse=False, loop=True, quality="low", height=200, width=200, key=None)


        # Insert Five9 logo
        five9logo_url = "https://raw.githubusercontent.com/mackensey31712/srr/main/five9log1.png"

        st.sidebar.image(five9logo_url, width=200)


        # Sidebar Title
        st.sidebar.markdown('# Select a **Filter:**')

        # Sidebar with a multi-select dropdown for 'Service' column filtering
        with st.sidebar:
            all_services_options = ['All'] + list(df['Service'].unique())
            selected_service = st.multiselect('Service - (Multi-Select)', all_services_options, default='All')

        # Apply filtering
        if 'All' in selected_service:
            df_filtered = df

        elif not selected_service:
            # If nothing is selected, display a message indicating all services are being displayed
            st.sidebar.markdown("<h3 style='color: red;'>Displaying All Services</h1>", unsafe_allow_html=True)
            df_filtered = df
        else:
            df_filtered = df[df['Service'].isin(selected_service)]

        # Sidebar with a dropdown for 'Month' column filtering
        with st.sidebar:
            selected_month = st.selectbox('Month', ['All'] + list(df_filtered['Month'].unique()))

        # Apply filtering
        if selected_month != 'All':
            df_filtered = df_filtered[df_filtered['Month'] == selected_month]
        else:
            df_filtered = df_filtered

        # Sidebar with a dropdown for 'Weekend?' column filtering
        with st.sidebar:
            selected_weekend = st.selectbox('Weekend?', ['All', 'Yes', 'No'])

        # Apply filtering
        if selected_weekend != 'All':
            df_filtered = df_filtered[df_filtered['Weekend?'] == selected_weekend]
        else:
            df_filtered = df_filtered

        # Sidebar with a dropdown for 'Working Hours?' column filtering
        with st.sidebar:
            selected_working_hours = st.selectbox('Working Hours?', ['All', 'Yes', 'No'])

        # Apply filtering
        if selected_working_hours != 'All':
            df_filtered = df_filtered[df_filtered['Working Hours?'] == selected_working_hours]
        else:
            df_filtered = df_filtered

        # Sidebar with a multi-select dropdown for 'SME (On It)' column filtering
        with st.sidebar:
            all_sme_options = ['All'] + list(df_filtered['SME (On It)'].unique())
            selected_sme_on_it = st.multiselect('SME (On It) - (Multi-Select)', all_sme_options, default='All')

        # # Apply filtering
        # if 'All' not in selected_sme_on_it:
        #     df_filtered = df_filtered[df_filtered['SME (On It)'].isin(selected_sme_on_it)]

        # Check the selection conditions
        if 'All' in selected_sme_on_it:
            # If 'All' is selected, display the whole filtered dataframe without a message
            st.sidebar.markdown("---")
        elif not selected_sme_on_it:
            # If nothing is selected, display a message indicating all SMEs are being displayed
            st.sidebar.markdown("<h3 style='color: red;'>Displaying All SMEs</h1>", unsafe_allow_html=True)
            
        else:
            # If specific SMEs are selected, filter the dataframe and display the result
            df_filtered = df_filtered[df_filtered['SME (On It)'].isin(selected_sme_on_it)]
            st.sidebar.markdown(
                "<h3 style='color: red;'>Displaying Selected SMEs</h1>",
                unsafe_allow_html=True)
            df_filtered = df_filtered



        # DataFrames for "In Queue" and "In Progress"
        df_inqueue = df_filtered[df_filtered['Status'] == 'In Queue']
        df_inqueue = df_inqueue[['Case #', 'Requestor','Service','Creation Timestamp', 'Message Link']]
        df_inprogress = df_filtered[df_filtered['Status'] == 'In Progress']
        df_inprogress = df_inprogress[['Case #', 'Requestor','Service','Creation Timestamp', 'SME (On It)', 'TimeTo: On It', 'Message Link']]

        # DataFrame was originaly placed here

        # Metrics
        df_filtered['TimeTo: On It Sec'] = df_filtered['TimeTo: On It'].apply(convert_to_seconds)
        df_filtered['TimeTo: Attended Sec'] = df_filtered['TimeTo: Attended'].apply(convert_to_seconds)
        # overall_avg_on_it = df_filtered['TimeTo: On It Sec'].mean()
        # overall_avg_attended = df_filtered['TimeTo: Attended Sec'].mean()
        # unique_case_count = calculate_metrics(df_filtered)

        # # Display metrics
        # col1, col3,col5 = st.columns(3)
        # with col1:
        #     st.metric(label="Interactions", value=unique_case_count)
        # with col3:
        #     st.metric("Overall Avg. TimeTo: On It", seconds_to_hms(overall_avg_on_it))
        # with col5:
        #     st.metric("Overall Avg. TimeTo: Attended", seconds_to_hms(overall_avg_attended))

        #-------------------------
        # Ensure 'TimeTo: On It' and 'TimeTo: Attended' are in timedelta format -----------------------------
        df_filtered['TimeTo: On It'] = pd.to_timedelta(df_filtered['TimeTo: On It'])
        df_filtered['TimeTo: Attended'] = pd.to_timedelta(df_filtered['TimeTo: Attended'])

        # Calculate the average seconds directly from 'TimeTo: On It' and 'TimeTo: Attended', and convert to 'hh:mm:ss'
        overall_avg_on_it_sec = df_filtered['TimeTo: On It'].dt.total_seconds().mean()
        overall_avg_attended_sec = df_filtered['TimeTo: Attended'].dt.total_seconds().mean()

        overall_avg_on_it_hms = seconds_to_hms(overall_avg_on_it_sec)
        overall_avg_attended_hms = seconds_to_hms(overall_avg_attended_sec)
        unique_case_count = calculate_metrics(df_filtered)

        # Display metrics
        col1, col3,col5 = st.columns(3)
        with col1:
            st.metric(label="Interactions", value=unique_case_count)
        with col3:
            st.metric("Overall Avg. TimeTo: On It", overall_avg_on_it_hms)
        with col5:
            st.metric("Overall Avg. TimeTo: Attended", overall_avg_attended_hms)

        #------------------------

        # Display "In Queue" DataFrame with count
        in_queue_count = len(df_inqueue)

        # Using columns to place text and animation side by side
        if in_queue_count == 0:
            col1, col2 = st.columns([0.3, 1.2])  # Adjust the ratio as needed for your layout
            with col1:
                st.title(f'In Queue (0)')
            with col2:
                # Display Lottie animation if count is 0
                st_lottie(lottie_clap, speed=1, height=100, width=200)  # Adjust height as needed
            with st.expander("Show Data", expanded=False):
                st.dataframe(df_inqueue, use_container_width=True)
        else:
            col1, col2 = st.columns([0.3, 1.2])  # Adjust the ratio as needed for your layout
            with col1:
                st.title(f'In Queue ({in_queue_count})')
            with col2:
                # Display Lottie animation if count is not 0
                st_lottie(lottie_queuing, speed=1, height=100, width=200)  # Adjust height as needed
            with st.expander("Show Data", expanded=False):
                st.dataframe(df_inqueue, use_container_width=True)


        # Display "In Progress" DataFrame with count
        in_progress_count = len(df_inprogress)
        if in_progress_count == 0:
            col1, col2 = st.columns([0.4, 1.2])  # Adjust the ratio as needed for your layout
            with col1:
                st.title(f'In Progress (0)')
            with col2:
                # Display Lottie animation if count is 0
                st_lottie(lottie_chill, speed=1, height=100, width=200)  # Adjust height as needed
            with st.expander("Show Data", expanded=False):
                st.dataframe(df_inprogress, use_container_width=True)
        else:
            col1, col2 = st.columns([0.4, 1.2])  # Adjust the ratio as needed for your layout
            with col1:
                st.title(f'In Progress ({in_progress_count})')
            with col2:
                # Display Lottie animation if count is not 0
                st_lottie(lottie_inprogress, speed=1, height=100, width=200)  # Adjust height as needed
            with st.expander("Show Data", expanded=False):
                st.dataframe(df_inprogress, use_container_width=True)

        filtered_columns = ['Case #', 'Service', 'Inquiry', 'Requestor', 'Creation Timestamp',
       'SME (On It)', 'On It Time', 'Attendee', 'Attended Timestamp',
       'Message Link', 'Message Link 0', 'Message Link 1', 'Message Link 2',
       'Status', 'Case Reason', 'AFI', 'AFI Comment', 'Article#',
       'TimeTo: On It (Raw)', 'TimeTo: Attended (Raw)','Month', 'Day', 'Weekend?',
       'Date Created', 'Working Hours?', 'Survey', 'Hour_Created']

        # Display the filtered dataframe
        st.title('Data')
        with st.expander('Show Data', expanded=False):
            st.dataframe(df_filtered[filtered_columns], use_container_width=True)


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

        # st.set_option('deprecation.showPyplotGlobalUse', False)

        # Instead of converting these columns to datetime, converting seconds to minutes or hours for a more interpretable visualization
        agg_month['TimeTo: On It Minutes'] = agg_month['TimeTo: On It Sec'] / 60
        agg_month['TimeTo: Attended Minutes'] = agg_month['TimeTo: Attended Sec'] / 60


        col1,col5 = st.columns(2)

        # Create an interactive bar chart using Altair

        # Adjust the column names to remove spaces and special characters
        agg_month.rename(columns={
            'TimeTo: On It Minutes': 'TimeTo_On_It_Minutes',
            'TimeTo: Attended Minutes': 'TimeTo_Attended_Minutes'
        }, inplace=True)

        agg_month_long = agg_month.melt(id_vars=['Month'],
                                        value_vars=['TimeTo_On_It_Minutes', 'TimeTo_Attended_Minutes'],
                                        var_name='Category',
                                        value_name='Minutes')

        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

        # Create a stacked bar chart with months ordered as specified
        chart = alt.Chart(agg_month_long).mark_bar().encode(
            x=alt.X('Month', sort=month_order),  # Use the 'sort' argument to order months
            y=alt.Y('Minutes', stack='zero'),  # Use stack='zero' for stacking
            color='Category',  # Color distinguishes the categories
            tooltip=['Month', 'Category', 'Minutes']  # Optional: add tooltip for interactivity
        ).properties(
            title='Monthly Response Times',
            width=600,
            height=400
        )

        # To display the chart in your Streamlit app
        with col1:
            st.write(chart)

        # Convert seconds to minutes directly for 'agg_service'
        agg_service['TimeTo_On_It_Minutes'] = agg_service['TimeTo: On It Sec'] / 60
        agg_service['TimeTo_Attended_Minutes'] = agg_service['TimeTo: Attended Sec'] / 60

        # Now, the DataFrame 'agg_service' contains correctly named columns for melting
        agg_service_long = agg_service.melt(id_vars=['Service'],
                                            value_vars=['TimeTo_On_It_Minutes', 'TimeTo_Attended_Minutes'],
                                            var_name='Category',
                                            value_name='Minutes')

        # Create a stacked bar chart
        chart2 = alt.Chart(agg_service_long).mark_bar().encode(
            x='Service',
            y=alt.Y('Minutes', stack='zero'),  # Use stack='zero' for stacking
            color='Category',  # Color distinguishes the categories
            tooltip=['Service', 'Category', 'Minutes']  # Optional: add tooltip for interactivity
        ).properties(
            title='Group Response Times',
            width=600,
            height=400
        )

        # To display the chart in your Streamlit app
        with col5:
            st.write(chart2)

        # Create an interactive bar chart  to show the 'unique case count' for each service
        chart3 = alt.Chart(df_filtered).mark_bar().encode(
            x='Service',
            y='count()',
            tooltip=['Service', 'count()']
        ).properties(
            title='Interaction Count',
            width=600,
            height=400
        )

        # To display the chart in your Streamlit app
        with col1:
            st.write(chart3)

        # Create an interactive bar chart using Altair to show the 'unique case count' for each 'SME (On It)'
        chart4 = alt.Chart(df_filtered).mark_bar().encode(
            y=alt.Y('SME (On It):N', sort='-x'),  # Sorting based on the count in descending order, ensure to specify ':N' for nominal data
            x=alt.X('count()', title='Unique Case Count'),
            tooltip=['SME (On It)', 'count()']
        ).properties(
            title='Interactions Handled',
            width=600,
            height=600
        )

        # To display the chart in your Streamlit app
        with col5:
            st.write(chart4)

        # Filter out rows where "Case Reason" or "Case #" is null (adjust column names as necessary)
        # df_filtered = df.dropna(subset=['Case #', 'Case Reason'])

        # Group by "Case Reason" and count "Case #" occurrences
        case_counts = df_filtered.groupby('Case Reason')['Service'].count().reset_index()

        # Sort the DataFrame by counts in ascending order
        case_counts_sorted = case_counts.sort_values(by='Service', ascending=True)

        # Generate a pie chart
        fig = px.pie(case_counts_sorted, values='Service', names='Case Reason', title='Distribution of Case Reasons')

        # Show the pie chart in the Streamlit app
        st.plotly_chart(fig)


        st.subheader('Interaction Count by Requestor')


        # Display a Dataframe where the rows are the 'Requestor', the columns would be the 'Service', and the values would be the count of each 'Service'

        # Create a pivot table using pandas
        pivot_df = df_filtered.pivot_table(index='Requestor', columns='Service', aggfunc='size', fill_value=0)

        # Reset the index so 'Requestor' becomes a regular column
        pivot_df.reset_index(inplace=True)

        # Setting up GridOptions for AgGrid
        gb = GridOptionsBuilder.from_dataframe(pivot_df)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=10)  # Enable pagination
        # gb.configure_side_bar(filters_panel=False, columns_panel=False)  # Enable side bar if you want filters and columns tool panel
        gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)

        gridOptions = gb.build()

        # Display the AgGrid component with the configured options
        AgGrid(pivot_df, gridOptions=gridOptions, update_mode=GridUpdateMode.MODEL_CHANGED, fit_columns_on_grid_load=True)


        # Creating the Summary Table where it sorts the SME (On It) column by first getting the total average TimeTo: On It and average TimeTo: Attended and then sorting it by the number of Interactions
        # and then by the highest average survey.

        # Group by 'SME (On It)' and calculate the required metrics including average survey
        # df_filtered['TimeTo: On It Sec'] = df_filtered['TimeTo: On It'].apply(convert_to_seconds)
        # df_filtered['TimeTo: Attended Sec'] = df_filtered['TimeTo: Attended'].apply(convert_to_seconds)

        df_grouped = df_filtered.groupby('SME (On It)').agg(
            Avg_On_It_Sec=pd.NamedAgg(column='TimeTo: On It Sec', aggfunc='mean'),
            Avg_Attended_Sec=pd.NamedAgg(column='TimeTo: Attended Sec', aggfunc='mean'),
            Number_of_Interactions=pd.NamedAgg(column='SME (On It)', aggfunc='count')
        ).reset_index()

        df_grouped['Total_Avg_Sec'] = df_grouped['Avg_On_It_Sec'] + df_grouped['Avg_Attended_Sec']
        df_sorted = df_grouped.sort_values(by=['Total_Avg_Sec', 'Number_of_Interactions'], ascending=[True, False])
        df_sorted['Avg_On_It'] = df_sorted['Avg_On_It_Sec'].apply(seconds_to_hms)
        df_sorted['Avg_Attended'] = df_sorted['Avg_Attended_Sec'].apply(seconds_to_hms)

        # Rename 'SME (On It)' column to 'SME'
        df_sorted.rename(columns={'SME (On It)': 'SME'}, inplace=True)

        st.subheader("SME Summary Table")
        st.dataframe(df_sorted[['SME', 'Avg_On_It', 'Avg_Attended', 'Number_of_Interactions']].set_index('SME'))


        # Auto-update every 5 minutes
        refresh_rate = 120  # 300 seconds = 5 minutes
        time.sleep(refresh_rate)
        st.rerun()

if __name__ == '__main__':
    main()