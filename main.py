import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.title("Inventory Dashboard")

st.text("ใช้ข้อมูล: Date | Product | Stock | Demand | Daily_Usage | Cost_per_Order | Holding_Cost")

st.markdown(
    """
    | ฟิลด์               | ความหมาย                              | หน่วย (ตัวอย่าง)                                       |
    | ------------------ | ------------------------------------- | --------------------------------------------------- |
    | **Date**           | วันที่ของรายการ                          | YYYY-MM-DD เช่น 2025-10-01                         |
    | **Product**        | ชื่อหรือรหัสสินค้า                         | ไม่มีหน่วย (เป็น text)                                  |
    | **Stock**          | ปริมาณสินค้าคงเหลือ                      | ชิ้น (หรือหน่วยนับสินค้านั้น ๆ)                        |    
    | **Demand**         | ความต้องการของลูกค้าในวันนั้น              | ชิ้น/วัน                                            |
    | **Daily_Usage**    | ปริมาณที่ถูกขายจริงต่อวัน                    | ชิ้น/วัน                                           |
    | **Cost_per_Order** | ต้นทุนต่อการสั่งซื้อ 1 ครั้ง                  | บาท/ครั้ง                                         |
    | **Holding_Cost**   | ต้นทุนการเก็บรักษาสินค้าต่อหน่วยต่อปี          | บาท/ชิ้น/ปี                                       |
    """
)

uploaded_file = st.file_uploader("เลือกไฟล์ Excel หรือ CSV", type=["csv", "xlsx"])

if uploaded_file is not None:
    # อ่านไฟล์
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.subheader("ข้อมูลที่อัปโหลด")
    st.dataframe(df)

    # -------------------------------
    # Inventory Status (ตารางรวมคงเหลือ)
    # -------------------------------
    if "Product" in df.columns and "Stock" in df.columns:
        st.subheader("📦 Inventory Status")
        stock_summary = df.groupby("Product")["Stock"].sum().reset_index()
        st.dataframe(stock_summary)
        fig_stock = px.bar(stock_summary, x="Product", y="Stock", title="คงเหลือสินค้า (Stock)")
        st.plotly_chart(fig_stock, use_container_width=True)

    # -------------------------------
    # Forecast (แนวโน้มจากข้อมูลย้อนหลัง)
    # -------------------------------
    if "Date" in df.columns and "Demand" in df.columns:
        st.subheader("📈 Forecast Demand")
        df["Date"] = pd.to_datetime(df["Date"])
        demand_trend = df.groupby("Date")["Demand"].sum().reset_index()

        # Forecast แบบง่าย (Moving Average)
        demand_trend["Forecast"] = demand_trend["Demand"].rolling(window=3, min_periods=1).mean()

        fig_forecast = px.line(demand_trend, x="Date", y=["Demand", "Forecast"],
                               title="แนวโน้มการใช้สินค้า (Demand vs Forecast)")
        st.plotly_chart(fig_forecast, use_container_width=True)

    # -------------------------------
    # EOQ Calculation per Product (รวมทุกแถวต่อสินค้า)
    # -------------------------------
    required_cols = {"Product", "Stock", "Demand", "Cost_per_Order", "Holding_Cost"}
    if required_cols.issubset(df.columns):
        st.subheader("📐 EOQ per Product")

        # รวมข้อมูลต่อสินค้า
        grouped = df.groupby("Product").agg({
            "Demand": "sum",             # รวมความต้องการ
            "Stock": "sum",              # รวม Stock ปัจจุบัน
            "Cost_per_Order": "mean",    # ค่าเฉลี่ย Cost per Order
            "Holding_Cost": "mean"       # ค่าเฉลี่ย Holding Cost
        }).reset_index()

        # คำนวณ EOQ
        grouped["EOQ"] = np.sqrt(2 * grouped["Demand"] * grouped["Cost_per_Order"] / grouped["Holding_Cost"])
        grouped["EOQ"] = grouped["EOQ"].round()

        st.dataframe(grouped[["Product", "Stock", "EOQ"]])

        # กราฟเปรียบเทียบ Stock กับ EOQ
        fig_eoq = px.bar(grouped, x="Product", y=["Stock", "EOQ"],
                         barmode='group', title="เปรียบเทียบ Stock ปัจจุบันกับ EOQ")
        st.plotly_chart(fig_eoq, use_container_width=True)

    # -------------------------------
    # Alert: แนวโน้ม Stockout ใน 7 วัน
    # -------------------------------
    if {"Product", "Stock", "Daily_Usage"}.issubset(df.columns):
        st.subheader("⚠️ Stockout Alert")
        alerts = []
        for _, row in df.iterrows():
            days_left = row["Stock"] / row["Daily_Usage"] if row["Daily_Usage"] > 0 else np.inf
            if days_left < 7:
                alerts.append(f"สินค้า {row['Product']} มีแนวโน้ม Stockout ใน {days_left:.1f} วัน")

        if alerts:
            for alert in alerts:
                st.error(alert)
        else:
            st.success("ไม่มีสินค้าใดมีแนวโน้ม Stockout ใน 7 วัน ✅")
