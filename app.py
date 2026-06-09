import numpy as np
import streamlit as st
import pandas as pd

# 設定網頁標題與圖示
st.set_page_config(page_title="蒙地卡羅退休提領預測", page_icon="📊", layout="wide")

st.title("📊 蒙地卡羅退休提領預測（隨機報酬 + 隨機通膨 + 動態提領 + 退休金流入 + 大額支出 + 匯出功能）")
st.write("這是一個全功能隨機模型，考量**投資報酬與通膨波動、動態護欄策略、政府/公司退休金固定流入**，並可加入**一次性大額支出**、**提領下限保障**，最後可**一鍵匯出結果**。")
st.write("---")

# 1. 主頁面建立輸入參數
st.subheader("⚙️ 模擬參數設定")

# 第一排：資產與首年提領
row1_col1, row1_col2, row1_col3 = st.columns(3)
with row1_col1:
    initial_assets_wan = st.number_input(
        "1. 現有資產（初始金額，單位：萬元）", min_value=0.0, value=1000.0, step=10.0, format="%.0f"
    )
    initial_assets = initial_assets_wan * 10000.0
with row1_col2:
    first_year_pension_wan = st.number_input(
        "2. 退休首年預估生活開銷（單位：萬元/年）", min_value=0.0, value=40.0, step=1.0, format="%.0f"
    )
    first_year_pension = first_year_pension_wan * 10000.0
with row1_col3:
    num_years = st.number_input(
        "3. 模擬年數（預估退休生活長度）", min_value=1, max_value=100, value=30, step=1
    )

# 第二排：政府 / 公司退休金流入設定
st.write("")
st.markdown("##### 🏦 政府 / 公司退休金流入設定（如勞保年金、勞退、商業年金）")
enable_pension_flow = st.checkbox("我有其他固定退休金或年金流入（啟用後可降低自有資產提領壓力）", value=True)

pension_flow_annual = 0.0
start_flow_year = 0

if enable_pension_flow:
    flow_col1, flow_col2 = st.columns(2)
    with flow_col1:
        pension_flow_type = flow_col1.radio("退休金領取頻率：", ["按月領取", "按年領取"], horizontal=True)
        if pension_flow_type == "按月領取":
            pension_flow_month = flow_col1.number_input("預估每月可領金額（萬元/月）", min_value=0.0, value=2.0, step=0.1)
            pension_flow_annual = pension_flow_month * 12.0 * 10000.0
        else:
            pension_flow_year_input = flow_col1.number_input("預估每年可領金額（萬元/年）", min_value=0.0, value=24.0, step=1.0)
            pension_flow_annual = pension_flow_year_input * 10000.0
    with flow_col2:
        start_flow_year = flow_col2.number_input(
            "從退休後第幾年開始領取？（0 代表退休第一天就開始領，如 65 歲領）", 
            min_value=0, max_value=int(num_years)-1, value=0, step=1
        )

# 第三排：投資與通膨參數
st.write("")
st.markdown("##### 📈 投資市場與通膨參數")
row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
with row2_col1:
    expected_annual_return = st.number_input(
        "4. 預估資產年報酬率 (%)", min_value=-50.0, max_value=100.0, value=6.0, step=0.1
    ) / 100
with row2_col2:
    annual_volatility = st.number_input(
        "5. 報酬率標準差 (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.1
    ) / 100
with row2_col3:
    expected_inflation = st.number_input(
        "6. 預估平均通膨率 (%)", min_value=-10.0, max_value=50.0, value=3.8, step=0.1
    ) / 100
with row2_col4:
    inflation_volatility = st.number_input(
        "7. 通膨率標準差 (%)", min_value=0.0, max_value=50.0, value=3.0, step=0.1
    ) / 100

# 第四排：動態提領機制設定
st.write("")
st.markdown("##### 🛡️ 退休中期動態調整選項")
enable_dynamic = st.checkbox("開啟「蓋頓-克林格護欄策略」型動態提領（大跌少領、大漲多領）", value=True)

# 先定義預設值（避免作用域問題）
enable_floor = False
floor_amount_wan = 0.0

if enable_dynamic:
    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        guard_drop = st.slider("安全護欄：當總資產跌破購買力幾 % 時，自動減少 10% 提領？", 50, 90, 70, 5, format="%d%%") / 100
    with row3_col2:
        guard_rise = st.slider("繁榮護欄：當總資產超過購買力幾 % 時，自動增加 5% 提領？", 110, 160, 130, 5, format="%d%%") / 100

    st.write("")
    enable_floor = st.checkbox("🔒 設定提領下限（維持最低生活開銷）", value=False)
    if enable_floor:
        floor_amount_wan = st.number_input(
            "最低年提領金額（萬元／年）",
            min_value=0.0, value=20.0, step=1.0, format="%.0f"
        )

# 第五排：一次性大額支出設定
st.write("")
st.markdown("##### 💰 一次性大額支出設定（如購車、房屋修繕、子女婚禮等）")
col_le1, col_le2 = st.columns(2)

with col_le1:
    enable_large_expense_1 = st.checkbox("啟用大額支出 1", value=False)
    large_expense_amount_1 = 0.0
    large_expense_year_1 = 0
    if enable_large_expense_1:
        large_expense_amount_1_wan = st.number_input(
            "支出金額（萬元）", min_value=0.0, value=50.0, step=1.0, key="le1_amt"
        )
        large_expense_amount_1 = large_expense_amount_1_wan * 10000.0
        large_expense_year_1 = st.number_input(
            "發生年份（退休後第幾年，0 為第 1 年）",
            min_value=0, max_value=int(num_years)-1, value=5, step=1, key="le1_year"
        )

with col_le2:
    enable_large_expense_2 = st.checkbox("啟用大額支出 2", value=False)
    large_expense_amount_2 = 0.0
    large_expense_year_2 = 0
    if enable_large_expense_2:
        large_expense_amount_2_wan = st.number_input(
            "支出金額（萬元）", min_value=0.0, value=30.0, step=1.0, key="le2_amt"
        )
        large_expense_amount_2 = large_expense_amount_2_wan * 10000.0
        large_expense_year_2 = st.number_input(
            "發生年份（退休後第幾年，0 為第 1 年）",
            min_value=0, max_value=int(num_years)-1, value=10, step=1, key="le2_year"
        )

st.write("")
# 建立大按鈕
submit_button = st.button("🚀 開始蒙地卡羅模擬", type="primary", use_container_width=True)
st.write("---")

num_simulations = 10000

# 2. 執行模擬邏輯
if submit_button:
    
    with st.spinner("模擬計算中，請稍候..."):
        # 產生隨機矩陣
        random_returns = np.random.normal(loc=expected_annual_return, scale=annual_volatility, size=(num_years, num_simulations))
        random_inflations = np.random.normal(loc=expected_inflation, scale=inflation_volatility, size=(num_years, num_simulations))
        
        # 初始化
        current_assets = np.full(num_simulations, initial_assets)
        pensions = np.full(num_simulations, first_year_pension)          # 基礎生活開銷
        external_pension_flow = np.full(num_simulations, pension_flow_annual)
        purchasing_power_baseline = np.full(num_simulations, initial_assets)
        
        # 初始化提領下限（若有啟用）
        min_floor = floor_amount_wan * 10000.0 if enable_floor else 0.0
        min_floor_array = np.full(num_simulations, min_floor)
        
        is_failed = np.zeros(num_simulations, dtype=bool)
        fail_years = np.full(num_simulations, num_years) 
        
        # 初始化 5 等分歷史紀錄
        p10_history = [initial_assets / 10000.0]
        p30_history = [initial_assets / 10000.0]
        p50_history = [initial_assets / 10000.0]
        p70_history = [initial_assets / 10000.0]
        p90_history = [initial_assets / 10000.0]
        
        # 逐年模擬計算
        for year in range(num_years):
            if year > 0:
                # 基礎通膨調整
                pensions = np.where(~is_failed, pensions * (1 + random_inflations[year]), pensions)
                external_pension_flow = np.where(~is_failed, external_pension_flow * (1 + random_inflations[year]), external_pension_flow)
                purchasing_power_baseline = purchasing_power_baseline * (1 + random_inflations[year])
                
                # 下限跟著通膨成長
                if enable_dynamic and enable_floor:
                    min_floor_array = np.where(~is_failed, min_floor_array * (1 + random_inflations[year]), min_floor_array)
                
                # 動態提領護欄邏輯
                if enable_dynamic:
                    active_mask = ~is_failed
                    asset_ratio = np.where(active_mask, current_assets / purchasing_power_baseline, 1.0)
                    
                    # 護欄調整
                    pensions = np.where(active_mask & (asset_ratio < guard_drop), pensions * 0.90, pensions)
                    pensions = np.where(active_mask & (asset_ratio > guard_rise), pensions * 1.05, pensions)
                    
                    # 套用提領下限（只對基礎生活開銷）
                    if enable_floor:
                        pensions = np.where(active_mask, np.maximum(pensions, min_floor_array), pensions)
            
            # 處理一次性大額支出
            extra_expense = np.zeros(num_simulations)
            if enable_large_expense_1 and year == large_expense_year_1:
                extra_expense += large_expense_amount_1
            if enable_large_expense_2 and year == large_expense_year_2:
                extra_expense += large_expense_amount_2
            
            total_pensions = pensions + extra_expense
            
            # 計算今年實際淨提領
            current_year_flow = np.where(year >= start_flow_year, external_pension_flow, 0.0)
            net_withdrawal = np.maximum(total_pensions - current_year_flow, 0.0)
                
            active_mask = ~is_failed
            current_assets = np.where(active_mask, current_assets - net_withdrawal, 0)
            
            just_failed = active_mask & (current_assets < 0)
            is_failed |= just_failed
            fail_years[just_failed] = year 
            
            active_mask = ~is_failed
            current_assets = np.where(active_mask, current_assets, 0)
            current_assets = np.where(active_mask, current_assets * (1 + random_returns[year]), 0)
            
            # 統計 5 等分百分位數（轉換為萬元）
            p10_history.append(np.percentile(current_assets, 10) / 10000.0)
            p30_history.append(np.percentile(current_assets, 30) / 10000.0)
            p50_history.append(np.percentile(current_assets, 50) / 10000.0)
            p70_history.append(np.percentile(current_assets, 70) / 10000.0)
            p90_history.append(np.percentile(current_assets, 90) / 10000.0)

        # 計算指標
        success_count = np.sum(~is_failed)
        success_rate = (success_count / num_simulations) * 100
        avg_life_expectancy = np.mean(fail_years)
        successful_final_assets = current_assets[~is_failed]
        median_remaining = np.median(successful_final_assets) if len(successful_final_assets) > 0 else 0

        # 3. 網頁呈現結果
        st.subheader("📊 模擬報告結果")
        st.caption(f"已成功運行 {num_simulations:,} 次隨機路徑模擬")
        
        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            st.metric(label="💡 退休計畫成功率", value=f"{success_rate:.2f}%")
        with res_col2:
            st.metric(label="⏳ 資產預期平均壽命", value=f"{avg_life_expectancy:.1f} 年")
        with res_col3:
            if success_rate > 0:
                st.metric(label="💰 成功情境下期末資產中位數", value=f"{median_remaining / 10000:,.0f} 萬元")
            else:
                st.metric(label="💰 成功情境下期末資產中位數", value="0 萬元")

        if success_rate >= 80:
            st.success("🎉 恭喜！目前的資產配置與提領計畫具有極高的安全度。")
        elif 50 <= success_rate < 80:
            st.warning("⚠️ 警告：成功率處於中等水準，建議調整提領金額或優化投資組合。")
        else:
            st.error("🚨 嚴重警告：在當前隨機參數下破產機率極高，強烈建議優化策略。")
            
        st.write("---")
        
        # 呈現 5 等分期末最終金額的統計區塊
        st.subheader(f"🏁 第 {num_years} 年期末最終資產估算 (5等分走勢)")
        
        final_cols = st.columns(5)
        with final_cols[0]:
            st.metric(
                label="🔴 極度悲觀 (10th)", 
                value=f"{p10_history[-1]:,.0f} 萬元" if p10_history[-1] > 0 else "0 萬元 (已破產)"
            )
        with final_cols[1]:
            st.metric(
                label="🟠 相對悲觀 (30th)", 
                value=f"{p30_history[-1]:,.0f} 萬元" if p30_history[-1] > 0 else "0 萬元 (已破產)"
            )
        with final_cols[2]:
            st.metric(
                label="🔵 中位數常態 (50th)", 
                value=f"{p50_history[-1]:,.0f} 萬元" if p50_history[-1] > 0 else "0 萬元 (已破產)"
            )
        with final_cols[3]:
            st.metric(
                label="🟡 相對樂觀 (70th)", 
                value=f"{p70_history[-1]:,.0f} 萬元" if p70_history[-1] > 0 else "0 萬元 (已破產)"
            )
        with final_cols[4]:
            st.metric(
                label="🟢 極度樂觀 (90th)", 
                value=f"{p90_history[-1]:,.0f} 萬元" if p90_history[-1] > 0 else "0 萬元 (已破產)"
            )
            
        st.write("")
        
        # 折線圖
        st.subheader("📈 退休資產 5 等分走勢模擬 (單位：萬元)")
        chart_data = pd.DataFrame({
            "1. 極度悲觀 (10th)": p10_history,
            "2. 相對悲觀 (30th)": p30_history,
            "3. 中位數常態 (50th)": p50_history,
            "4. 相對樂觀 (70th)": p70_history,
            "5. 極度樂觀 (90th)": p90_history
        }, index=list(range(num_years + 1)))
        
        st.line_chart(chart_data)

        # ----- 新增：匯出結果按鈕 -----
        st.write("")
        st.subheader("📥 匯出模擬結果")
        
        # 匯出 1：資產走勢數據
        csv_chart = chart_data.to_csv(index=True).encode('utf-8')
        st.download_button(
            label="下載資產走勢數據 (CSV)",
            data=csv_chart,
            file_name="retirement_asset_paths.csv",
            mime="text/csv",
        )
        
        # 匯出 2：彙總指標
        summary_data = {
            "指標": [
                "成功率 (%)",
                "資產平均壽命 (年)",
                "成功情境期末資產中位數 (萬元)",
                "模擬年數",
                "模擬次數"
            ],
            "數值": [
                f"{success_rate:.2f}",
                f"{avg_life_expectancy:.1f}",
                f"{median_remaining / 10000:,.0f}",
                num_years,
                num_simulations
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        csv_summary = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="下載彙總指標 (CSV)",
            data=csv_summary,
            file_name="retirement_summary.csv",
            mime="text/csv",
        )
        
else:
    st.info("👆 請在上方調整您的參數，並點擊「開始蒙地卡羅模擬」按鈕開始預測。")