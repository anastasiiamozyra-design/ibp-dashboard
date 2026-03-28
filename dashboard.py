import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(page_title="IBP-Style Planning Dashboard", layout="centered")

st.title("IBP-Style Supply Chain Planning Tool (Simulation)")
st.write("Interactive simulation of demand, inventory, and replenishment decisions based on IBP-style planning logic.")

st.header("Inputs")
base_demand = st.slider("Average daily demand", min_value=50, max_value=200, value=100, step=5)
demand_variability = st.slider("Demand variability", min_value=5, max_value=30, value=12, step=1)
lead_time = st.slider("Lead time (days)", min_value=1, max_value=10, value=3, step=1)
initial_inventory = st.slider("Initial inventory", min_value=100, max_value=500, value=220, step=10)
service_factor = st.slider("Safety stock factor", min_value=0.2, max_value=2.0, value=0.8, step=0.1)
forecast_window = st.slider("Forecast window (days)", min_value=3, max_value=14, value=7, step=1)
order_up_to_days = st.slider("Coverage after replenishment (days)", min_value=1, max_value=7, value=3, step=1)

np.random.seed(42)
days = 60
noise = np.random.normal(0, demand_variability, days)
trend = np.linspace(0, 10, days)
seasonality = 8 * np.sin(np.arange(days) / 5)
demand = np.maximum(20, (base_demand + trend + seasonality + noise)).round().astype(int)

df = pd.DataFrame({
    "day": np.arange(1, days + 1),
    "demand": demand
})

order_quantity = 250
before_reorder_point = 120


def simulate_inventory(data, mode="before"):
    inventory = initial_inventory
    pipeline_orders = []
    records = []

    for i in range(len(data)):
        day = int(data.loc[i, "day"])
        actual_demand = int(data.loc[i, "demand"])

        arrivals_today = sum(qty for arrival_day, qty in pipeline_orders if arrival_day == day)
        inventory += arrivals_today
        pipeline_orders = [(d, q) for d, q in pipeline_orders if d != day]

        sales = min(inventory, actual_demand)
        stockout = max(0, actual_demand - inventory)
        inventory -= sales

        if mode == "after":
            history_start = max(0, i - forecast_window + 1)
            demand_history = data.loc[history_start:i, "demand"]
            forecast_mean = demand_history.mean()
            forecast_std = demand_history.std(ddof=0) if len(demand_history) > 1 else 0

            safety_stock = service_factor * forecast_std * np.sqrt(lead_time)
            reorder_point = forecast_mean * lead_time + safety_stock
            target_stock = forecast_mean * (lead_time + order_up_to_days) + safety_stock
            inventory_position = inventory + sum(q for _, q in pipeline_orders)

            if inventory_position < reorder_point:
                order_qty = max(0, int(round(target_stock - inventory_position)))
                if order_qty > 0:
                    pipeline_orders.append((day + lead_time, order_qty))
            else:
                order_qty = 0
        else:
            if inventory <= before_reorder_point:
                order_qty = order_quantity
                pipeline_orders.append((day + lead_time, order_qty))
            else:
                order_qty = 0

        records.append({
            "day": day,
            "demand": actual_demand,
            "closing_inventory": inventory,
            "stockout": stockout,
            "order": order_qty,
        })

    result = pd.DataFrame(records)
    total_demand = result["demand"].sum()
    total_sales = total_demand - result["stockout"].sum()

    kpis = {
        "avg_inventory": round(float(result["closing_inventory"].mean()), 1),
        "service_level": round(float(total_sales / total_demand * 100), 1),
        "total_stockouts": int(result["stockout"].sum()),
    }
    return result, kpis


before_df, before_kpis = simulate_inventory(df, "before")
after_df, after_kpis = simulate_inventory(df, "after")

st.header("Results")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Before")
    st.metric("Average inventory", before_kpis["avg_inventory"])
    st.metric("Service level (%)", before_kpis["service_level"])
    st.metric("Total stockouts", before_kpis["total_stockouts"])

with col2:
    st.subheader("After")
    st.metric("Average inventory", after_kpis["avg_inventory"])
    st.metric("Service level (%)", after_kpis["service_level"])
    st.metric("Total stockouts", after_kpis["total_stockouts"])

st.header("Impact")
service_improvement = round(after_kpis["service_level"] - before_kpis["service_level"], 1)
stockout_reduction = round((before_kpis["total_stockouts"] - after_kpis["total_stockouts"]) / before_kpis["total_stockouts"] * 100, 1) if before_kpis["total_stockouts"] else 0.0
inventory_change = round(after_kpis["avg_inventory"] - before_kpis["avg_inventory"], 1)

st.write(f"Service level improvement: **{service_improvement} pp**")
st.write(f"Stockout reduction: **{stockout_reduction}%**")
st.write(f"Average inventory change: **{inventory_change}**")

st.header("Demand data")
st.dataframe(df, use_container_width=True)

st.header("Daily simulation")
view = st.radio("View scenario", ["Before", "After"], horizontal=True)
if view == "Before":
    st.dataframe(before_df, use_container_width=True)
else:
    st.dataframe(after_df, use_container_width=True)

st.header("Business interpretation")

st.write("This tool demonstrates how demand variability and lead time impact service level and inventory decisions.")

st.write("It reflects simplified planning logic used in tools such as SAP IBP or o9, where forecasting, safety stock, and replenishment decisions are integrated.")
