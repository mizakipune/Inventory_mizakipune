import streamlit as st
import pandas as pd
from datetime import date
if "product_checked" not in st.session_state:
    st.session_state.product_checked = False

st.set_page_config(
    page_title="Inventory App",
    layout="centered"
)

file = "inventory_mizaki.xlsx"

inventory = pd.read_excel(file, sheet_name="Inventory")
sales = pd.read_excel(file, sheet_name="Sales")

st.set_page_config(page_title="Inventory App", layout="wide")

st.title("📦 Inventory Management System")

menu = st.sidebar.selectbox(
    "Menu",
    [
        "Dashboard",
        "Add Product",
        "Update Stock",
        "Record Sale",
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

            with pd.ExcelWriter(file) as writer:
                inventory.to_excel(writer,sheet_name="Inventory",index=False)
                sales.to_excel(writer,sheet_name="Sales",index=False)

            st.success("✅ Product Added Successfully")

# ---------------- UPDATE STOCK ----------------

elif menu == "Update Stock":

    st.subheader("Update Stock")

    product = st.selectbox("Product", inventory["Product"].unique())
    details = st.selectbox("Details", inventory["Details"].unique())
    size = st.selectbox("Size", inventory["Size"].unique())
    colour = st.selectbox("Colour", inventory["Colours"].unique())

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

        with pd.ExcelWriter(file) as writer:
            inventory.to_excel(writer, sheet_name="Inventory", index=False)
            sales.to_excel(writer, sheet_name="Sales", index=False)

        st.success("Stock Updated Successfully")

# ---------------- RECORD SALE ----------------

elif menu == "Record Sale":

    st.subheader("Record Sale")

    product = st.selectbox("Product", inventory["Product"].unique())
    details = st.selectbox("Details", inventory["Details"].unique())
    size = st.selectbox("Size", inventory["Size"].unique())
    colour = st.selectbox("Colour", inventory["Colours"].unique())

    qty_input = st.text_input("Enter Quantity For Sale")

    # ---------------- CHECK PRODUCT ----------------

    if st.button("Check Product"):

        product_data = inventory[
            (inventory["Product"] == product) &
            (inventory["Details"] == details) &
            (inventory["Size"] == size) &
            (inventory["Colours"] == colour)
        ]

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
            st.write("Available Stock:", stock_qty)
            st.write("Cost Price:", cost)
            st.write("Sale Price:", sp)

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

    if st.session_state.product_checked:

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

            cost = st.session_state.cost
            sp1 = st.session_state.sp            
            profit = (real_sale - cost) * qty

            previous_qty = st.session_state.stock
            remaining_qty = previous_qty - qty
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

            # Update stock
            inventory.loc[
                (inventory["Product"] == product) &
                (inventory["Details"] == details) &
                (inventory["Size"] == size) &
                (inventory["Colours"] == colour),
                "Quantity"
            ] -= qty

            with pd.ExcelWriter(file) as writer:
                inventory.to_excel(writer, sheet_name="Inventory", index=False)
                sales.to_excel(writer, sheet_name="Sales", index=False)

            st.success("✅ Sale Recorded Successfully")


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