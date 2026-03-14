import streamlit as st
import pandas as pd
from datetime import date
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

if "product_checked" not in st.session_state:
    st.session_state.product_checked = False

st.set_page_config(
    page_title="Inventory App",
    layout="centered"
)

# file = "inventory_mizaki.xlsx"
# inventory = pd.read_excel(file, sheet_name="Inventory")
# sales = pd.read_excel(file, sheet_name="Sales")

scope = [
"https://spreadsheets.google.com/feeds",
"https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "service_account.json", scope
)

client = gspread.authorize(creds)
sheet = client.open("inventory_mizaki")

inventory_sheet = sheet.worksheet("Inventory")
sales_sheet = sheet.worksheet("Sales")

inventory = pd.DataFrame(inventory_sheet.get_all_records())
sales = pd.DataFrame(sales_sheet.get_all_records())

text_columns = ["Product","Details","Size","Colours"]
for col in text_columns:
    inventory[col] = inventory[col].astype(str)
inventory["Cost Price"] = pd.to_numeric(inventory["Cost Price"], errors="coerce")
inventory["Sale Price"] = pd.to_numeric(inventory["Sale Price"], errors="coerce")
inventory["Quantity"] = pd.to_numeric(inventory["Quantity"], errors="coerce")

st.set_page_config(page_title="Inventory App", layout="wide")

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
    cost = st.text_input("Cost Price")
    sp = st.text_input("Sale Price")
    qty = st.text_input("Quantity")

    if st.button("Add Product"):
        # Check if product already exists
        mask = (
            (inventory["Product"] == product) &
            (inventory["Details"] == details) &
            (inventory["Size"] == size) &
            (inventory["Colours"] == colour)
        )

        if inventory[mask].shape[0] > 0:
            st.warning("⚠ Product already available. Please update stock instead.")

        else:
            new_product = pd.DataFrame({

                "Date":[date.today()],
                "Product":[product],
                "Details":[details],
                "Size":[size],
                "Colours":[colour],
                "Quantity":[int(qty)],
                "Cost Price":[float(cost)],
                "Sale Price":[float(sp)]

            })

            inventory = pd.concat([inventory,new_product],ignore_index=True)

            inventory_sheet.update([inventory.columns.values.tolist()] + inventory.values.tolist())
            sales_sheet.update([sales.columns.values.tolist()] + sales.values.tolist())

            st.success("✅ Product Added Successfully")

# ---------------- UPDATE STOCK ----------------

elif menu == "Update Stock":

    st.subheader("Update Stock")

    product = st.selectbox(
        "Product",
        sorted(inventory["Product"].unique()),
        key="sale_product"
    )

    product_df = inventory[inventory["Product"] == product]

    # -------- DETAILS (filtered by product) --------
    details = st.selectbox(
        "Details",
        sorted(product_df["Details"].unique()),
        key="sale_details"
    )

    details_df = product_df[product_df["Details"] == details]

    # -------- SIZE (filtered by product + details) --------
    size = st.selectbox(
        "Size",
        sorted(details_df["Size"].unique()),
        key="sale_size"
    )

    size_df = details_df[details_df["Size"] == size]

    # -------- COLOUR (filtered by product + details + size) --------
    colour = st.selectbox(
        "Colour",
        sorted(size_df["Colours"].unique()),
        key="sale_colour"
    )

    qty_input = st.text_input("Enter Quantity")

    if st.button("Update Stock"):
        qty = int(qty_input)

        mask = (
            (inventory["Product"] == product) &
            (inventory["Details"] == details) &
            (inventory["Size"] == size) &
            (inventory["Colours"] == colour)
        )

        inventory.loc[mask, "Quantity"] = inventory.loc[mask, "Quantity"] + qty

        inventory_sheet.update([inventory.columns.values.tolist()] + inventory.values.tolist())
        sales_sheet.update([sales.columns.values.tolist()] + sales.values.tolist())

        st.success("Stock Updated Successfully")

# ---------------- RECORD SALE ----------------

elif menu == "Record Sale":

    product = st.selectbox(
        "Product",
        sorted(inventory["Product"].unique()),
        key="sale_product"
    )

    product_df = inventory[inventory["Product"] == product]

    # -------- DETAILS (filtered by product) --------
    details = st.selectbox(
        "Details",
        sorted(product_df["Details"].unique()),
        key="sale_details"
    )

    details_df = product_df[product_df["Details"] == details]

    # -------- SIZE (filtered by product + details) --------
    size = st.selectbox(
        "Size",
        sorted(details_df["Size"].unique()),
        key="sale_size"
    )

    size_df = details_df[details_df["Size"] == size]

    # -------- COLOUR (filtered by product + details + size) --------
    colour = st.selectbox(
        "Colour",
        sorted(size_df["Colours"].unique()),
        key="sale_colour"
    )

    qty_input = st.text_input("Enter Quantity For Sale")

    # ---------------- CHECK PRODUCT ----------------

    if st.button("Check Product"):

        product_data = size_df[size_df["Colours"] == colour]

        if product_data.empty:
            st.error("❌ Product not found in inventory")
            st.session_state.product_checked = False

        else:

            cost = float(product_data["Cost Price"].values[0])
            sp = float(product_data["Sale Price"].values[0])
            stock_qty = int(product_data["Quantity"].values[0])

            st.session_state.product_checked = True
            st.session_state.cost = cost
            st.session_state.sp = sp
            st.session_state.stock = stock_qty

            st.success("✅ Product Found")

            col1, col2, col3 = st.columns(3)

            col1.metric("Available Stock", stock_qty)
            col2.metric("Cost Price", cost)
            col3.metric("Sale Price", sp)

            # -------- CHECK QUANTITY --------

            if qty_input:
                try:
                    qty = int(qty_input)

                    if qty > stock_qty:
                        st.error(f"❌ Entered quantity not available. Only {stock_qty} items in stock.")
                    else:
                        st.success("✅ Quantity available for sale")

                except:
                    st.error("Enter valid numeric quantity")

    # ---------------- ENTER SALE PRICE ----------------

    if st.session_state.get("product_checked", False):

        customer_name = st.text_input("Enter Customer Name")
        real_sale_input = st.text_input("Enter Real Sale Price")

        if st.button("Save Sale"):

            if not qty_input:
                st.error("Enter quantity")
                st.stop()

            try:
                qty = int(qty_input)
            except:
                st.error("Quantity must be number")
                st.stop()

            if qty > st.session_state.stock:
                st.error(f"❌ Only {st.session_state.stock} items available in stock")
                st.stop()

            if not real_sale_input:
                st.error("Enter real sale price")
                st.stop()

            try:
                real_sale = float(real_sale_input)
            except:
                st.error("Invalid sale price")
                st.stop()

            if not customer_name:
                st.error("Enter customer name")
                st.stop()

            cost = float(st.session_state.cost)
            sp1 = float(st.session_state.sp)

            previous_qty = int(st.session_state.stock)
            remaining_qty = previous_qty - qty

            profit_per_item = real_sale - cost
            profit = profit_per_item * qty

            total_costprice = cost * qty
            total_saleprice = real_sale * qty

            new_sale = pd.DataFrame({

                "Date":[date.today()],
                "Customer Name":[customer_name],
                "Product":[product],
                "Details":[details],
                "Size":[size],
                "Colours":[colour],
                "Previous Quantity":[previous_qty],
                "Quantity Sold":[qty],
                "Cost Price":[cost],
                "Sale Price":[sp1],
                "Quantity":[remaining_qty],
                "Real Sale Price":[real_sale],
                "Total Cost Price":[total_costprice],
                "Total Sale Price":[total_saleprice],
                "Profit":[profit]

            })

            sales = pd.concat([sales,new_sale],ignore_index=True)

            # Update inventory
            inventory.loc[
                (inventory["Product"] == product) &
                (inventory["Details"] == details) &
                (inventory["Size"] == size) &
                (inventory["Colours"] == colour),
                "Quantity"
            ] = remaining_qty

            inventory_sheet.update([inventory.columns.values.tolist()] + inventory.values.tolist())
            sales_sheet.update([sales.columns.values.tolist()] + sales.values.tolist())

            st.success("✅ Sale Recorded Successfully")

# ---------------- EIDT SALE PRODUCT ------------------------------------------
####=============================================================================
elif menu == "Edit Sale":

    st.subheader("Edit Sale Record")

    # Show sales table
    st.dataframe(sales)

    # Select row
    row_index = st.selectbox(
        "Select Row to Edit",
        sales.index
    )

    selected_row = sales.loc[row_index]

    st.write("Selected Record")
    st.write(selected_row)

    # Editable fields
    new_customer = st.text_input(
        "Customer Name",
        value=selected_row["Customer Name"]
    )

    new_qty = st.text_input(
        "Quantity Sold",
        value=str(selected_row["Quantity Sold"])
    )

    new_sale_price = st.text_input(
        "Real Sale Price",
        value=str(selected_row["Real Sale Price"])
    )

    if st.button("Update Sale Record"):

        try:
            new_qty = int(new_qty)
            new_sale_price = float(new_sale_price)
        except:
            st.error("Enter valid numbers")
            st.stop()

        cost = float(selected_row["Cost Price"])

        previous_qty = int(selected_row["Previous Quantity"])
        remaining_qty = previous_qty - new_qty

        total_cost = cost * new_qty
        total_sale = new_sale_price * new_qty
        new_profit = (new_sale_price - cost) * new_qty

        # Update dataframe
        sales.loc[row_index,"Customer Name"] = new_customer
        sales.loc[row_index,"Quantity Sold"] = new_qty
        sales.loc[row_index,"Real Sale Price"] = new_sale_price
        sales.loc[row_index,"Total Cost Price"] = total_cost
        sales.loc[row_index,"Total Sale Price"] = total_sale
        sales.loc[row_index,"Profit"] = new_profit
        sales.loc[row_index,"Quantity"] = remaining_qty

        # Save Excel
        inventory_sheet.update([inventory.columns.values.tolist()] + inventory.values.tolist())
        sales_sheet.update([sales.columns.values.tolist()] + sales.values.tolist())

        st.success("Sale updated successfully")
############# Inventory Record ++++++++++++++++++++++++++++++++++++++++++++++++
####################################################################################
elif menu == "Edit Inventory":

    st.subheader("Edit Inventory Record")

    # Show sales table
    st.dataframe(inventory)

    # Select row
    row_index = st.selectbox(
        "Select Row to Edit",
        inventory.index
    )

    selected_row = inventory.loc[row_index]

    st.write("Selected Record")
    st.write(selected_row)

    # Editable fields
    new_product = st.text_input(
        "Product",
        value=selected_row["Product"]
    )

    new_details = st.text_input(
        "Details",
        value=selected_row["Details"]
    )

    new_size = st.text_input(
        "Size",
        value=selected_row["Size"]
    )

    
    new_clr = st.text_input(
        "Colours",
        value=str(selected_row["Colours"])
    )

    new_cost_price = st.text_input(
        "Cost Price",
        value=str(selected_row["Cost Price"])
    )

    new_sale_price = st.text_input(
        "Sale Price",
        value=str(selected_row["Sale Price"])
    )

    if st.button("Update inventory Record"):

        try:
            new_cost_price = float(new_cost_price)
            new_sale_price = float(new_sale_price)
        except:
            st.error("Enter valid numbers")
            st.stop()

        # Update dataframe
        inventory.loc[row_index,"Product"] = new_product
        inventory.loc[row_index,"Details"] = new_details
        inventory.loc[row_index,"Size"] = new_size
        inventory.loc[row_index,"Colours"] = new_clr
        inventory.loc[row_index,"Cost Price"] = new_cost_price
        inventory.loc[row_index,"Sale Price"] = new_sale_price
       
        # Save Excel
        inventory_sheet.update([inventory.columns.values.tolist()] + inventory.values.tolist())
        sales_sheet.update([sales.columns.values.tolist()] + sales.values.tolist())

        st.success("inventory updated successfully")

# ---------------- SEARCH PRODUCT ----------------

elif menu == "Search Product":

    st.subheader("Search Product")

    search = st.text_input("Enter Product Name")

    if search:

        result = inventory[
            inventory["Product"].str.contains(search,case=False)
        ]

        st.dataframe(result)

# ---------------- SALES REPORT ----------------

elif menu == "Sales Report":

    st.subheader("Datewise Sales Report")

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

    st.subheader("Download Reports")

    inv_csv = inventory.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Inventory Report",
        inv_csv,
        "inventory_report.csv",
        "text/csv"
    )

    sales_csv = sales.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Sales Report",
        sales_csv,
        "sales_report.csv",
        "text/csv"
    )