import streamlit as st
import pandas as pd
import plotly.express as px

st.title("อัปโหลดไฟล์ Excel หรือ CSV เพื่อแสดงตารางและกราฟ")

uploaded_file = st.file_uploader("เลือกไฟล์ Excel หรือ CSV", type=["csv", "xlsx"])

if uploaded_file is not None:
    # อ่านไฟล์
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("แสดงข้อมูลในไฟล์:")
    st.dataframe(df)

    # เลือกคอลัมน์สำหรับกราฟ
    st.subheader("เลือกคอลัมน์เพื่อทำกราฟ")
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    all_columns = df.columns.tolist()

    x_axis = st.selectbox("เลือกแกน X", all_columns)
    y_axis = st.multiselect("เลือกแกน Y (เลือกได้หลายคอลัมน์)", numeric_columns)

    chart_type = st.radio("เลือกประเภทกราฟ", ["Line", "Bar", "Scatter"])

    if x_axis and y_axis:
        if chart_type == "Line":
            fig = px.line(df, x=x_axis, y=y_axis, title="Line Chart")
        elif chart_type == "Bar":
            fig = px.bar(df, x=x_axis, y=y_axis, title="Bar Chart", barmode="group")
        else:  # Scatter
            # แสดง scatter แยกเป็นหลายกราฟ
            fig = px.scatter(df, x=x_axis, y=y_axis[0], title=f"Scatter Chart ({y_axis[0]})")
            for col in y_axis[1:]:
                fig.add_scatter(x=df[x_axis], y=df[col], mode="markers", name=col)

        st.plotly_chart(fig, use_container_width=True)
