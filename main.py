import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Inventory Dashboard", layout="wide")

st.title("📦 Inventory Dashboard")
st.markdown("""
ระบบติดตามสินค้าคงคลังหลายประเภทต่อวัน พร้อมคำนวณ EOQ และพยากรณ์สินค้าหมด
""")

st.info("ใช้ข้อมูล: Date | Product | Stock | Demand | Daily_Usage | Cost_per_Order | Holding_Cost")

with st.expander("❓ ความหมายของแต่ละฟิลด์"):
    st.markdown(
        """
        | ฟิลด์               | ความหมาย                              | หน่วย (ตัวอย่าง)                                       |
        | ------------------ | ------------------------------------- | --------------------------------------------------- |
        | **Date**           | วันที่ของรายการ                          | YYYY-MM-DD เช่น 2025-01-01                         |
        | **Product**        | ชื่อหรือรหัสสินค้า                         | ไม่มีหน่วย (text)                                  |
        | **Stock**          | ปริมาณสินค้าคงเหลือ                      | ชิ้น                                                |    
        | **Demand**         | ความต้องการของลูกค้าในวันนั้น              | ชิ้น/วัน                                            |
        | **Daily_Usage**    | ปริมาณที่ถูกขายจริงต่อวัน                    | ชิ้น/วัน                                           |
        | **Cost_per_Order** | ต้นทุนต่อการสั่งซื้อ 1 ครั้ง                  | บาท/ครั้ง                                         |
        | **Holding_Cost**   | ต้นทุนการเก็บรักษาสินค้าต่อหน่วยต่อปี          | บาท/ชิ้น/ปี                                       |
        """
    )

uploaded_file = st.file_uploader("เลือกไฟล์ Excel หรือ CSV", type=["csv", "xlsx"])

if uploaded_file is not None:
    with st.spinner("กำลังโหลดข้อมูล..."):
        # อ่านไฟล์
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.subheader("📄 ข้อมูลที่อัปโหลด")
        st.dataframe(df, use_container_width=True)

        # แปลงค่าที่จำเป็นเป็นตัวเลข
        for col in ["Stock", "Demand", "Daily_Usage", "Cost_per_Order", "Holding_Cost"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # -------------------------------
        # Inventory Status (ล่าสุดต่อ Product)
        # -------------------------------
        if {"Product", "Stock"}.issubset(df.columns):
            st.subheader("📊 Inventory Status (Stock ล่าสุด)")
            latest_stock = df.sort_values("Date").groupby("Product").last().reset_index()

            st.dataframe(latest_stock[["Product", "Stock"]])
            fig_stock = px.bar(latest_stock, x="Product", y="Stock",
                                title="Stock ล่าสุดของแต่ละสินค้า",
                                text="Stock")
            fig_stock.update_layout(yaxis_title="Stock (ชิ้น)")
            st.plotly_chart(fig_stock, use_container_width=True)

        # -------------------------------
        # EOQ Calculation per Product + Days to Stock Out
        # -------------------------------
        required_cols = {"Product", "Stock", "Daily_Usage", "Cost_per_Order", "Holding_Cost"}
        if required_cols.issubset(df.columns):
            st.subheader("📐 EOQ per Product & Stock-out Forecast")

            grouped = df.groupby("Product").agg({
                "Stock": "min",
                "Daily_Usage": "mean",
                "Cost_per_Order": "mean",
                "Holding_Cost": "mean"
            }).reset_index()

            grouped["Annual_Demand"] = grouped["Daily_Usage"] * 365
            grouped["EOQ"] = np.sqrt(2 * grouped["Annual_Demand"] * grouped["Cost_per_Order"] / grouped["Holding_Cost"]).round()
            grouped["Days_to_Stockout"] = np.where(grouped["Daily_Usage"] > 0,
                                                   (grouped["Stock"] / grouped["Daily_Usage"]).round(1),
                                                   np.inf)

            # ตาราง EOQ
            st.dataframe(grouped[["Product", "Stock", "EOQ", "Days_to_Stockout"]], use_container_width=True)

            # กราฟเปรียบเทียบ Stock vs EOQ
            fig_eoq = px.bar(grouped, x="Product", y=["Stock", "EOQ"],
                             barmode='group',
                             title="เปรียบเทียบ Stock ล่าสุดกับ EOQ",
                             text_auto=True)
            fig_eoq.update_layout(yaxis_title="จำนวน (ชิ้น)")
            st.plotly_chart(fig_eoq, use_container_width=True)

            # -------------------------------
            # Alert: Stock ต่ำกว่า EOQ และใกล้หมด
            # -------------------------------
            with st.expander("⚠️ Stock-out Alert", expanded=True):
                for _, row in grouped.iterrows():
                    msg = f"สินค้า {row['Product']} จะหมดใน {row['Days_to_Stockout']} วัน"
                    if row["Stock"] < row["EOQ"]:
                        st.error(msg + " ⚠️ ต่ำกว่า EOQ! ควรสั่งเพิ่ม")
                    elif row["Days_to_Stockout"] <= 7:
                        st.warning(msg + " ⚠️ ใกล้หมด")
                    else:
                        st.success(msg + " ✅ เพียงพอ")

            # -------------------------------
            # Monthly EOQ Forecast (2 เดือน)
            # -------------------------------
            months_forecast = 2
            forecast_data = []

            for _, row in grouped.iterrows():
                stock = row["Stock"]
                monthly_usage = row["Daily_Usage"] * 30
                eoq = row["EOQ"]
                for month in range(1, months_forecast + 1):
                    stock -= monthly_usage
                    alert = ""
                    if stock < eoq:
                        alert = "⚠️ ต่ำกว่า EOQ! สั่งเพิ่ม"
                        stock += eoq
                    elif stock <= monthly_usage:
                        alert = "⚠️ ใกล้หมด"
                    forecast_data.append({
                        "Product": row["Product"],
                        "Month": month,
                        "Forecast_Stock": round(stock, 1),
                        "EOQ": eoq,
                        "Alert": alert
                    })

            forecast_df = pd.DataFrame(forecast_data)
            st.subheader("📊 Monthly EOQ Forecast")
            st.dataframe(forecast_df, use_container_width=True)
