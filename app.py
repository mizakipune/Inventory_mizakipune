import streamlit as st
import pandas as pd
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Inventory App", layout="centered")

st.title("📦 Inventory Management System")

# ---------------- GOOGLE CONNECTION ----------------

scope = [
"https://spreadsheets.google.com/feeds",
"https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)

client = gspread.authorize(creds)

sheet = client.open_by_key("14d0tx3xeL94Fls_0S78DqfBRhPD_22Kz7_8s7X0ILK8")

inventory_sheet = sheet.worksheet("Inventory")
sales_sheet = sheet.worksheet("Sales")

# ---------------- LOAD DATA ----------------

inventory = pd.DataFrame(inventory_sheet.get_all_records())
sales = pd.DataFrame(sales_sheet.get_all_records())

# ---------------- DATA CLEAN ----------------

text_columns = ["SKU","Product","Details","Size","Colours"]

for col in text_columns:
    if col in inventory.columns:
        inventory[col] = inventory[col].astype(str)

numeric_columns = ["Cost Price","Sale Price","Quantity"]

for col in numeric_columns:
    if col in inventory.columns:
        inventory[col] = pd.to_numeric(inventory[col], errors="coerce")

# ---------------- SAVE FUNCTION ----------------

def save_to_google():

    inventory_clean = inventory.fillna("").astype(str)
    sales_clean = sales.fillna("").astype(str)

    inventory_sheet.update(
        [inventory_clean.columns.tolist()] + inventory_clean.values.tolist()
    )

    sales_sheet.update(
        [sales_clean.columns.tolist()] + sales_clean.values.tolist()
    )

# ---------------- SKU GENERATOR ----------------

def generate_sku():

    if inventory.empty:
        return "SKU001"

    last = inventory["SKU"].str.replace("SKU","").astype(int).max()

    new = last + 1

    return f"SKU{str(new).zfill(3)}"

# ---------------- MENU ----------------

menu = st.sidebar.selectbox(
    "Menu",
    [
        "Dashboard",
        "Add Product",
        "Update Stock",
        "Record Sale",
        "Edit Sale",
        "Edit Inventory",
        "Search Product",
        "Sales Report",
        "Download Reports"
    ]
)

# ---------------- DASHBOARD ----------------

if menu == "Dashboard":

    st.subheader("Inventory Dashboard")

    if not sales.empty:

        sold = sales.groupby("SKU")["Quantity Sold"].sum().reset_index()

        summary = pd.merge(
            inventory,
            sold,
            on="SKU",
            how="left"
        )

        summary["Quantity Sold"] = summary["Quantity Sold"].fillna(0)
        summary["Remaining"] = summary["Quantity"] - summary["Quantity Sold"]

    else:

        summary = inventory.copy()
        summary["Quantity Sold"] = 0
        summary["Remaining"] = summary["Quantity"]

    total_profit = sales["Profit"].sum() if not sales.empty else 0

    col1,col2 = st.columns(2)

    col1.metric("Total Products", len(inventory))
    col2.metric("Total Profit", int(total_profit))

    st.dataframe(summary)

# ---------------- ADD PRODUCT ----------------

elif menu == "Add Product":

    st.subheader("Add Product")

    product = st.text_input("Product")
    details = st.text_input("Details")
    size = st.text_input("Size")
    colour = st.text_input("Colour")

    cost = st.number_input("Cost Price", min_value=0.0)
    sp = st.number_input("Sale Price", min_value=0.0)
    qty = st.number_input("Quantity", min_value=0)

    if st.button("Add Product"):

        mask = (
            (inventory["Product"] == product) &
            (inventory["Details"] == details) &
            (inventory["Size"] == size) &
            (inventory["Colours"] == colour)
        )

        if inventory[mask].shape[0] > 0:

            st.warning("⚠ Product already exists. Use Update Stock.")

        else:

            sku = generate_sku()

            new_product = pd.DataFrame({

                "SKU":[sku],
                "Date":[date.today()],
                "Product":[product],
                "Details":[details],
                "Size":[size],
                "Colours":[colour],
                "Quantity":[qty],
                "Cost Price":[cost],
                "Sale Price":[sp]

            })

            inventory = pd.concat([inventory,new_product],ignore_index=True)

            save_to_google()

            st.success(f"✅ Product Added (SKU: {sku})")

# ---------------- UPDATE STOCK ----------------

elif menu == "Update Stock":

    st.subheader("Update Stock")

    product = st.selectbox(
        "Product",
        sorted(inventory["Product"].unique())
    )

    product_df = inventory[inventory["Product"] == product]

    details = st.selectbox(
        "Details",
        sorted(product_df["Details"].unique())
    )

    details_df = product_df[product_df["Details"] == details]

    size = st.selectbox(
        "Size",
        sorted(details_df["Size"].unique())
    )

    size_df = details_df[details_df["Size"] == size]

    colour = st.selectbox(
        "Colour",
        sorted(size_df["Colours"].unique())
    )

    qty = st.number_input("Add Quantity", min_value=1)

    if st.button("Update Stock"):

        product_row = size_df[size_df["Colours"] == colour]

        if product_row.empty:

            st.error("Product not found")

        else:

            sku = product_row["SKU"].values[0]

            inventory.loc[inventory["SKU"] == sku, "Quantity"] += qty

            save_to_google()

            st.success(f"Stock Updated for SKU {sku}")

# ---------------- RECORD SALE ----------------

elif menu == "Record Sale":

    st.subheader("Record Sale")

    sku = st.selectbox("Select SKU", inventory["SKU"])

    product_row = inventory[inventory["SKU"]==sku].iloc[0]

    st.write(product_row[["Product","Details","Size","Colours"]])

    qty = st.number_input("Quantity Sold", min_value=1)

    real_sale = st.number_input("Real Sale Price", min_value=0.0)

    customer = st.text_input("Customer Name")

    if st.button("Save Sale"):

        stock = int(product_row["Quantity"])

        if qty > stock:
            st.error("Not enough stock")
            st.stop()

        cost = float(product_row["Cost Price"])

        remaining = stock - qty

        profit = (real_sale - cost) * qty

        new_sale = pd.DataFrame({

            "Date":[date.today()],
            "Customer Name":[customer],
            "SKU":[sku],
            "Product":[product_row["Product"]],
            "Quantity Sold":[qty],
            "Cost Price":[cost],
            "Real Sale Price":[real_sale],
            "Profit":[profit]

        })

        sales = pd.concat([sales,new_sale],ignore_index=True)

        inventory.loc[inventory["SKU"]==sku,"Quantity"] = remaining

        save_to_google()

        st.success("Sale Recorded")

# ---------------- EDIT SALE ----------------

elif menu == "Edit Sale":

    st.subheader("Edit Sale")

    st.dataframe(sales)

    row = st.selectbox("Select Row", sales.index)

    new_customer = st.text_input(
        "Customer",
        sales.loc[row,"Customer Name"]
    )

    if st.button("Update"):

        sales.loc[row,"Customer Name"] = new_customer

        save_to_google()

        st.success("Sale Updated")

# ---------------- EDIT INVENTORY ----------------

elif menu == "Edit Inventory":

    st.subheader("Edit Inventory")

    st.dataframe(inventory)

    row = st.selectbox("Select Row", inventory.index)

    new_price = st.number_input(
        "Sale Price",
        value=float(inventory.loc[row,"Sale Price"])
    )

    if st.button("Update"):

        inventory.loc[row,"Sale Price"] = new_price

        save_to_google()

        st.success("Inventory Updated")

# ---------------- SEARCH ----------------

elif menu == "Search Product":

    search = st.text_input("Search Product")

    if search:

        result = inventory[
            inventory["Product"].str.contains(search,case=False)
        ]

        st.dataframe(result)

# ---------------- SALES REPORT ----------------

elif menu == "Sales Report":

    if not sales.empty:

        sales["Date"] = pd.to_datetime(sales["Date"])

        start = st.date_input("Start Date")
        end = st.date_input("End Date")

        report = sales[
            (sales["Date"]>=pd.to_datetime(start)) &
            (sales["Date"]<=pd.to_datetime(end))
        ]

        st.dataframe(report)

        st.metric("Total Profit", int(report["Profit"].sum()))

# ---------------- DOWNLOAD REPORT ----------------

elif menu == "Download Reports":

    inv_csv = inventory.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Inventory",
        inv_csv,
        "inventory_report.csv"
    )

    sales_csv = sales.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Sales",
        sales_csv,
        "sales_report.csv"
    )