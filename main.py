import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Inventory Dashboard", layout="wide")

st.title("📦 Inventory Dashboard")
st.markdown("""
ระบบติดตามสินค้าคงคลังพร้อมคำนวณ EOQ และพยากรณ์สินค้าแต่ละประเภท
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
        # Combined Inventory Summary
        # -------------------------------
        required_cols = {"Product", "Stock", "Daily_Usage", "Cost_per_Order", "Holding_Cost"}
        if required_cols.issubset(df.columns):
            st.subheader("📋 Inventory Summary")

            # รวมข้อมูลล่าสุดต่อ Product
            latest = df.sort_values("Date").groupby("Product").last().reset_index()

            summary = latest.copy()
            summary["Annual_Demand"] = latest["Daily_Usage"] * 365
            summary["EOQ"] = np.sqrt(2 * summary["Annual_Demand"] * summary["Cost_per_Order"] / summary["Holding_Cost"]).round()
            summary["Days_to_Stockout"] = np.where(summary["Daily_Usage"] > 0,
                                                (summary["Stock"] / summary["Daily_Usage"]).round(1),
                                                np.inf)

            # สร้างข้อความ Alert
            def generate_alert(row):
                days = row["Days_to_Stockout"]
                if row["Stock"] < row["EOQ"]:
                    return f"⚠️ ต่ำกว่า EOQ! จะหมดใน {days} วัน ควรสั่งเพิ่ม"
                elif days <= 7:
                    return f"⚠️ ใกล้หมด! จะหมดใน {days} วัน ควรสั่งเพิ่ม"
                else:
                    return f"✅ เพียงพอ จะหมดใน {days} วัน"

            summary["Alert"] = summary.apply(generate_alert, axis=1)

            # แสดงตารางเดียว
            st.dataframe(summary[["Product", "Stock", "Days_to_Stockout", "EOQ", "Alert"]], use_container_width=True)
        
        # -------------------------------
        # Monthly EOQ Forecast (1 เดือน)
        # -------------------------------
        months_forecast = 1
        forecast_data = []

        for _, row in summary.iterrows():
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
        st.subheader("📈 Monthly EOQ Forecast (1 เดือน)")
        st.dataframe(forecast_df, use_container_width=True)

        # กราฟเปรียบเทียบ Stock vs EOQ
        fig_eoq = px.bar(summary, x="Product", y=["Stock", "EOQ"],
                            barmode='group',
                            title="เปรียบเทียบ Stock ล่าสุดกับ EOQ",
                            text_auto=True)
        fig_eoq.update_layout(yaxis_title="จำนวน (ชิ้น)")
        st.plotly_chart(fig_eoq, use_container_width=True)