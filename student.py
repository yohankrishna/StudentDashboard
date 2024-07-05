# Libraries
import streamlit as st
import plotly.express as px
import pandas as pd
import base64
import warnings
from fpdf import FPDF
import plotly.io as pio
import io
import tempfile

def generate_pdf_report(df, filename, figs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for i, row in df.iterrows():
        pdf.cell(200, 10, txt=f"Student Name: {row['Student Name']}, Student ID: {row['Student ID']}", ln=True)
        pdf.cell(200, 10,
                 txt=f"Domain Test -01: {row['Domain Test -01']}, Domain Test -02: {row['Domain Test -02']}",
                 ln=True)
        pdf.cell(200, 10,
                 txt=f"Assignment grades: {row['Assignment grades']}, Attendance records: {row['Attendance records']}",
                 ln=True)
        pdf.cell(200, 10,
                 txt=f"Participation levels (in the classroom): {row['Participation levels (in the classroom)']}",
                 ln=True)
        pdf.cell(200, 10, txt="", ln=True)  # Add a blank line for spacing

    for fig in figs:
        img_buf = fig_to_img(fig)

        # Create a temporary file for each image
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            tmpfile.write(img_buf.getbuffer())
            tmpfile.flush()
            pdf.image(tmpfile.name, x=10, y=None, w=190)  # Adjust x, y, w as needed for layout

    # Create a temporary file for the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_file:
        pdf.output(tmp_pdf_file.name)

    # Read the temporary PDF file into a BytesIO object
    with open(tmp_pdf_file.name, 'rb') as f:
        pdf_output = io.BytesIO(f.read())

    b64 = base64.b64encode(pdf_output.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Download PDF Report</a>'
    return href

def fig_to_img(fig):
    img_buf = io.BytesIO()
    pio.write_image(fig, img_buf, format="png")
    img_buf.seek(0)
    return img_buf

def generate_excel_report(df, filename):
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)

        b64 = base64.b64encode(output.read()).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">Download Excel Report</a>'
        return href
    except Exception as e:
        st.error(f"Error generating Excel report: {str(e)}")

# Participation level
def participation_level_calc(df, name):
    df_filtered = df[df["Course (Course Id, course Name)"] == name]
    count_high = df_filtered["Participation levels (in the classroom)"].value_counts().get("High", 0)
    count_low = df_filtered["Participation levels (in the classroom)"].value_counts().get("Low", 0)
    count_med = df_filtered["Participation levels (in the classroom)"].value_counts().get("Medium", 0)
    a = {'High': count_high, 'Medium': count_med, 'Low': count_low}
    f = pd.DataFrame.from_dict(a, orient='index', columns=['Count'])

    # Display the DataFrame as a table
    # st.table(f)
    b = {'High': (count_high / (count_low + count_med + count_high)) * 100,
         'Medium': (count_med / (count_low + count_med + count_high)) * 100,
         'Low': (count_low / (count_low + count_med + count_high)) * 100}
    ff = pd.DataFrame.from_dict(b, orient='index', columns=['Percentage'])
    f = pd.concat([f, ff], axis=1)
    return f

# Analyze function
def analyze_relationships(df):
    # Consistency between Domain Test 1 & 2
    df['Score Difference'] = abs(df['Domain Test -01'] - df['Domain Test -02'])
    consistent_students = df.sort_values(by='Score Difference').head(10)[['Student ID','Student Name','Score Difference']]

    # Attendance impact
    attendance_ranges = pd.cut(df['Attendance records'], bins=[0, 25, 50, 75, 100], labels=['0-25', '26-50', '51-75', '76-100'])
    attendance_analysis = df.groupby(attendance_ranges).agg({
        'Assignment grades': 'mean',
        'Domain Test -01': 'mean',
        'Domain Test -02': 'mean'
    }).reset_index()

    # Students with large discrepancy
    df['Score Difference'] = abs(df['Domain Test -02'] - df['Domain Test -01'])
    largest_discrepancies = df.sort_values(by='Score Difference', ascending=False).head(10)[['Student ID','Student Name','Score Difference']]

    # Relation between participation levels, grades and attendance
    fig_scatter = px.scatter(df, x='Participation levels (in the classroom)', y='Assignment grades',
                             color='Attendance records',
                             hover_data=['Student Name'])

    return consistent_students, attendance_analysis, largest_discrepancies, fig_scatter

# Dashboard function
warnings.filterwarnings('ignore')
st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

# Page title
st.title("👨🏽‍💻 Student Dashboard")
st.markdown('<style>div.block-container{padding-top:2.5rem;}</style>', unsafe_allow_html=True)

# File upload
fl = st.file_uploader("📁 Upload only CSV files", type=["csv"])
if fl is not None:
    filename = fl.name
    st.write(filename)
    if filename.lower().endswith(".csv"):
        initial_df = pd.read_csv(filename)
        # st.write(df.columns) ---> View Column Names

        # Filtering students with marks greater than 0 in both tests
        if 'Domain Test -01' in initial_df.columns and 'Domain Test -02' in initial_df.columns:
            df = initial_df[(initial_df['Domain Test -01'] > 0) & (initial_df['Domain Test -02'] > 0)].copy()

        df4 = df.copy()

        # Sort and display data based on selected criteria
        def sort_and_display_data(df, sort_by):
            sorted_df = df.sort_values(by=sort_by, ascending=False)
            st.write(sorted_df)

        # Search bar with multiselect
        st.subheader("Search by Student ID")
        search_terms = st.multiselect("Search by Student ID", df["Student ID"].unique())

        # Filter the student data based on the selected search terms
        if search_terms:
            filtered_students = df[df["Student ID"].isin(search_terms)]
            if not filtered_students.empty:
                st.table(filtered_students)
            else:
                st.warning("No matching students found.")

            # Individual  student result
            st.subheader("Test Results Comparison")
            fig_result = px.bar(filtered_students, x="Student Name", y=["Domain Test -01", "Domain Test -02",
                                                                            "Assignment grades"], barmode="group")
            fig_result.update_xaxes(title="Student Name")
            fig_result.update_yaxes(title="Marks")
            st.plotly_chart(fig_result)

            # Performance analysis
            st.subheader("Performance Analysis")
            for index,row in filtered_students.iterrows():
                student_name = row["Student Name"]
                st.write(f"**Student Name:{student_name}**")
                domain_test_01_avg = row["Domain Test -01"]
                domain_test_02_avg = row["Domain Test -02"]
                score_difference = domain_test_02_avg - domain_test_01_avg

                if score_difference > 0:
                    performance_trend = "Improved"
                elif score_difference < 0:
                    performance_trend = "Declined"
                else:
                    performance_trend = "No Change"

                if domain_test_02_avg >= 85:
                    performance_level = "Excellent"
                    guidance_needed = "No"
                elif 70 <= domain_test_02_avg < 85:
                    performance_level = "Good"
                    guidance_needed = "Maybe"
                elif 50 <= domain_test_02_avg < 70:
                    performance_level = "Average"
                    guidance_needed = "Yes"
                else:
                    performance_level = "Poor"
                    guidance_needed = "Definitely"

                if score_difference < 0:
                    score_declined = abs(score_difference)
                    st.write(f"**Score Declined:** {score_declined:.2f}")
                else:
                    st.write(f"**Score Increased:** {score_difference:.2f}")
                st.write(f"**Performance Trend:** {performance_trend}")
                st.write(f"**Performance Level:** {performance_level}")
                st.write(f"**More Guidance Needed:** {guidance_needed}")

        col1, col2 = st.columns((2))

        # Sidebar
        st.sidebar.header("Select Filters")

        # Select sorting criteria
        sort_criteria = st.sidebar.selectbox("Sort Data By", ["Attendance", "Domain Test 1 Marks",
                                                                  "Domain Test 2 Marks", "Assignment Marks"])

        st.subheader(f"Sorted by {sort_criteria}")
        if sort_criteria == "Attendance":
            sort_and_display_data(df, "Attendance records")
        elif sort_criteria == "Domain Test 1 Marks":
            sort_and_display_data(df, "Domain Test -01")
        elif sort_criteria == "Domain Test 2 Marks":
            sort_and_display_data(df, "Domain Test -02")
        elif sort_criteria == "Assignment Marks":
            sort_and_display_data(df, "Assignment grades")

        # Attendance filter
        if "Attendance records" in df.columns:
            attendance = st.sidebar.slider("Select Attendance Range", min_value=0, max_value=100,
                                               step=25, value=0)
            if 0 < attendance <= 25:
                df = df[df["Attendance records"] <= 25]
            elif 25 < attendance <= 50:
                df = df[(df["Attendance records"] > 25) & (df["Attendance records"] <= 50)]
            elif 50 < attendance <= 75:
                df = df[(df["Attendance records"] > 50) & (df["Attendance records"] <= 75)]
            elif attendance > 75:
                df = df[df["Attendance records"] > 75]

        # Course filter
        course_type = st.sidebar.multiselect("Select Course", df["Course (Course Id, course Name)"].unique())
        if not course_type:
            df2 = df.copy()
        else:
            df2 = df[df["Course (Course Id, course Name)"].isin(course_type)]

        # Participation filter
        participation = st.sidebar.multiselect("Select Participation",
                                                   df2["Participation levels (in the classroom)"].unique())
        if not participation:
            df3 = df2.copy()
        else:
            df3 = df2[df["Participation levels (in the classroom)"].isin(participation)]

        # Filter Combinations
        if not course_type and not participation:
            filtered_df = df
        elif course_type and not participation:
            filtered_df = df[df["Course (Course Id, course Name)"].isin(course_type)]
        elif not course_type and participation:
            filtered_df = df[df["Participation levels (in the classroom)"].isin(course_type)]
        elif course_type and participation:
            filtered_df = df[df["Course (Course Id, course Name)"].isin(course_type) & df[
                    "Participation levels (in the classroom)"].isin(participation)]
        else:
            filtered_df = df

        # Bar graph
        category_df = filtered_df.groupby(by=["Student Name"], as_index=False)["Assignment grades"].sum()
        with col1:
            st.subheader("All Students Grades")
            fig = px.bar(category_df, x="Student Name", y="Assignment grades", template="plotly_dark")
            st.plotly_chart(fig)

        # Scatter graph
        category_df = filtered_df.groupby(by=["Student Name"], as_index=False)["Attendance records"].sum()
        with col2:
            st.subheader("All Students Attendance")
            fig1 = px.scatter(category_df, x="Student Name", y="Attendance records", template="plotly_dark")
            st.plotly_chart(fig1)

        # Pie chart
        st.subheader("Subject Comparison")
        fig2 = px.pie(df4, values="SL.No", names="Course (Course Id, course Name)", hole=0.3)
        fig2.update_traces(text=df4["Course (Course Id, course Name)"], textposition="outside")
        st.plotly_chart(fig2)

        # Treemap
        st.subheader("All Students Treemap")
        fig_treemap = px.treemap(filtered_df, path=['Student Name', 'Course (Course Id, course Name)',
                                                            'Participation levels (in the classroom)'], values='SL.No',
                                     color='Assignment grades', hover_data=['Domain Test -01', 'Domain Test -02'],
                                     color_continuous_scale='RdBu')
        st.plotly_chart(fig_treemap, use_container_width=True)

        # Displaying analysis function results
        consistent_students, attendance_analysis, largest_discrepancies, fig_scatter = analyze_relationships(df)
        st.subheader("Analysis Results")
        st.write("**Students with Consistent Scores**")
        st.write(consistent_students)
        st.write("**Attendance Analysis**")
        st.write(attendance_analysis)
        st.write("**Students with Largest Score Discrepancies**")
        st.write(largest_discrepancies)
        st.write('**Relation between Participation, Attendance and Grades**')
        st.plotly_chart(fig_scatter)

        # Display participation level
        col3, col4 = st.columns((2))
        with col3:
            f = participation_level_calc(df, 'MERN')
            st.write("**Course participation levels - MERN**")
            st.write(f)
        with col4:
            f = participation_level_calc(df, 'SAA-C03 , AWS')
            st.write("**Course participation levels - AWS**")
            st.write(f)

        # Class average
        class_avg_df = df.groupby('Course (Course Id, course Name)').agg({
                'Domain Test -01': 'mean',
                'Domain Test -02': 'mean'
            }).reset_index()
        st.write("**Class Average**")
        st.write(class_avg_df)

        # Finding students who got less than class average
        class_avg_df_DT_1 = df.groupby('Course (Course Id, course Name)').agg({
            'Domain Test -01': 'mean'
        }).reset_index()
        class_avg_df_DT_2 = df.groupby('Course (Course Id, course Name)').agg({
            'Domain Test -02': 'mean'
        }).reset_index()

        # Extracting average marks for MERN and AWS
        mern_avg_DT_1 = class_avg_df_DT_1[class_avg_df_DT_1['Course (Course Id, course Name)'] == 'MERN']['Domain Test -01'].values[0]
        aws_avg_DT_1 = class_avg_df_DT_1[class_avg_df_DT_1['Course (Course Id, course Name)'] == 'SAA-C03 , AWS'][
            'Domain Test -01'].values[0]

        mern_avg_DT_2 = class_avg_df_DT_2[class_avg_df_DT_2['Course (Course Id, course Name)'] == 'MERN']['Domain Test -02'].values[0]
        aws_avg_DT_2 = class_avg_df_DT_2[class_avg_df_DT_2['Course (Course Id, course Name)'] == 'SAA-C03 , AWS'][
            'Domain Test -02'].values[0]
        st.write("**Students with scores less than class average**")
        aws_students_DT_1 = df[(df['Course (Course Id, course Name)'] == 'SAA-C03 , AWS') &
                               ((df['Domain Test -01'] < aws_avg_DT_1))]
        sort_aws_students_DT_1 = aws_students_DT_1.sort_values('Domain Test -01',ascending=False)
        aws_students_DT_2 = df[(df['Course (Course Id, course Name)'] == 'SAA-C03 , AWS') &
                               ((df['Domain Test -02'] < aws_avg_DT_2))]
        sort_aws_students_DT_2 = aws_students_DT_2.sort_values('Domain Test -02',ascending=False)

        mern_students_DT_1 = df[(df['Course (Course Id, course Name)'] == 'SAA-C03 , AWS') &
                                ((df['Domain Test -01'] < mern_avg_DT_1))]
        sort_mern_students_DT_1 = mern_students_DT_1.sort_values('Domain Test -01',ascending=False)
        mern_students_DT_2 = df[(df['Course (Course Id, course Name)'] == 'SAA-C03 , AWS') &
                                ((df['Domain Test -02'] < mern_avg_DT_2))]
        sort_mern_students_DT_2 = mern_students_DT_2.sort_values('Domain Test -02',ascending=False)

        st.write("**MERN Students**")
        col5, col6 = st.columns(2)
        with col5:
            st.write("**Students who scored less than average in Domain Test-1**")
            st.table(sort_mern_students_DT_1[['Student ID', 'Student Name', 'Domain Test -01']].reset_index(drop=True))
        with col6:
            st.write("**Students who scored less than average in Domain Test-2**")
            st.table(sort_mern_students_DT_2[['Student ID', 'Student Name', 'Domain Test -02']].reset_index(drop=True))

        st.write("**AWS Students**")
        col7, col8 = st.columns(2)
        with col7:
            st.write("**Students who scored less than average in Domain Test-1**")
            st.table(sort_aws_students_DT_1[['Student ID', 'Student Name', 'Domain Test -01']].reset_index(drop=True))
        with col8:
            st.write("**Students who scored less than average in Domain Test-2**")
            st.table(sort_aws_students_DT_2[['Student ID', 'Student Name', 'Domain Test -02']].reset_index(drop=True))

        # Downloadable Reports
        st.sidebar.subheader("Download Reports")

        if st.sidebar.button("Download PDF Report"):
            pdf_link = generate_pdf_report(filtered_df, 'filtered_student_report.pdf',
                                           [fig, fig1, fig2, fig_treemap, fig_scatter])
            st.markdown(pdf_link, unsafe_allow_html=True)

        if st.sidebar.button("Download Excel Report"):
            excel_link = generate_excel_report(filtered_df, 'filtered_student_report.xlsx')
            st.markdown(excel_link, unsafe_allow_html=True)

    else:
        st.error("Unsupported file format. Please upload a CSV or Excel file.")