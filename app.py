import streamlit as st
import pandas as pd
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Inventory App", layout="centered")

# ---------------- SESSION STATE ----------------
if "product_checked" not in st.session_state:
    st.session_state.product_checked = False

# ---------------- GOOGLE SHEETS CONNECTION ----------------

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

# ---------------- DATA CLEANING ----------------

text_columns = ["Product","Details","Size","Colours"]

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

# ---------------- UI ----------------

st.title("📦 Inventory Management System")

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

        sold = sales.groupby(["Product","Colours"])["Quantity Sold"].sum().reset_index()

        summary = pd.merge(
            inventory,
            sold,
            on=["Product","Colours"],
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

    st.subheader("Add New Product")

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

            new_product = pd.DataFrame({

                "Date":[date.today()],
                "Product":[product],
                "Details":[details],
                "Size":[size],
                "Colours":[colour],
                "Quantity":[qty],
                "Cost Price":[cost],
                "Sale Price":[sp]

            })

            inventory.loc[len(inventory)] = new_product.iloc[0]

            save_to_google()

            st.success("✅ Product Added Successfully")

# ---------------- UPDATE STOCK ----------------

elif menu == "Update Stock":

    st.subheader("Update Stock")

    product = st.selectbox("Product", sorted(inventory["Product"].unique()))

    product_df = inventory[inventory["Product"] == product]

    details = st.selectbox("Details", sorted(product_df["Details"].unique()))

    details_df = product_df[product_df["Details"] == details]

    size = st.selectbox("Size", sorted(details_df["Size"].unique()))

    size_df = details_df[details_df["Size"] == size]

    colour = st.selectbox("Colour", sorted(size_df["Colours"].unique()))

    qty = st.number_input("Enter Quantity", min_value=1)

    if st.button("Update Stock"):

        mask = (
            (inventory["Product"] == product) &
            (inventory["Details"] == details) &
            (inventory["Size"] == size) &
            (inventory["Colours"] == colour)
        )

        inventory.loc[mask,"Quantity"] += qty

        save_to_google()

        st.success("Stock Updated Successfully")

# ---------------- RECORD SALE ----------------

elif menu == "Record Sale":

    st.subheader("Record Sale")

    product = st.selectbox("Product", sorted(inventory["Product"].unique()))

    product_df = inventory[inventory["Product"] == product]

    details = st.selectbox("Details", sorted(product_df["Details"].unique()))

    details_df = product_df[product_df["Details"] == details]

    size = st.selectbox("Size", sorted(details_df["Size"].unique()))

    size_df = details_df[details_df["Size"] == size]

    colour = st.selectbox("Colour", sorted(size_df["Colours"].unique()))

    qty = st.number_input("Enter Quantity For Sale", min_value=1)

    if st.button("Check Product"):

        product_data = size_df[size_df["Colours"] == colour]

        if product_data.empty:
            st.error("Product not found")
        else:

            cost = float(product_data["Cost Price"].values[0])
            sp = float(product_data["Sale Price"].values[0])
            stock = int(product_data["Quantity"].values[0])

            st.metric("Available Stock", stock)
            st.metric("Cost Price", cost)
            st.metric("Sale Price", sp)

# ---------------- EDIT SALE ----------------

elif menu == "Edit Sale":

    st.subheader("Edit Sale")

    st.dataframe(sales)

    row = st.selectbox("Select Row", sales.index)

    new_customer = st.text_input("Customer", sales.loc[row,"Customer Name"])

    if st.button("Update"):

        sales.loc[row,"Customer Name"] = new_customer

        save_to_google()

        st.success("Sale Updated")

# ---------------- EDIT INVENTORY ----------------

elif menu == "Edit Inventory":

    st.subheader("Edit Inventory")

    st.dataframe(inventory)

    row = st.selectbox("Select Row", inventory.index)

    new_product = st.text_input("Product", inventory.loc[row,"Product"])

    if st.button("Update Inventory"):

        inventory.loc[row,"Product"] = new_product

        save_to_google()

        st.success("Inventory Updated")

# ---------------- SEARCH PRODUCT ----------------

elif menu == "Search Product":

    search = st.text_input("Search Product")

    if search:

        result = inventory[
            inventory["Product"].str.contains(search, case=False)
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

# ---------------- DOWNLOAD REPORTS ----------------

elif menu == "Download Reports":

    inv_csv = inventory.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Inventory Report",
        inv_csv,
        "inventory_report.csv"
    )

    sales_csv = sales.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Sales Report",
        sales_csv,
        "sales_report.csv"
    )