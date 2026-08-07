import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import httpx
from fastapi import HTTPException

from app.core.config import settings


class BlueDartService:
    _jwt_token: str | None = None
    _token_expiry: float = 0  # Timestamp in epoch seconds

    @classmethod
    async def get_jwt_token(cls) -> str:
        """Retrieves and caches the JWT Token from Blue Dart Auth API."""
        current_time = time.time()
        # Return cached token if valid for at least another 60 seconds
        if cls._jwt_token and cls._token_expiry - current_time > 60:
            return cls._jwt_token

        headers = {
            "ClientID": settings.BLUEDART_CLIENT_ID,
            "clientSecret": settings.BLUEDART_CLIENT_SECRET,
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(timeout=settings.BLUEDART_TIMEOUT_MS / 1000) as client:
            response = await client.get(settings.BLUEDART_AUTH_URL, headers=headers)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Blue Dart Auth Failed: {response.text}"
                )

            data = response.json()
            cls._jwt_token = data.get("JWTToken")
            # Set cached expiration to ~1 hour from now
            cls._token_expiry = current_time + 3500
            return cls._jwt_token

    @classmethod
    async def check_serviceability(
        cls,
        pincode: str,
        product_code: str = "A",
        sub_product_code: str = "P"
    ) -> dict:
        """Checks if a pincode is eligible for delivery/pickup."""
        token = await cls.get_jwt_token()
        url = f"{settings.BLUEDART_BASE_URL}/in/transportation/finder/v1/GetServicesforPincodeAndProduct"

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "JWTToken": token
        }

        payload = {
            "pinCode": pincode,
            "ProductCode": product_code,
            "SubProductCode": sub_product_code,
            "PackType": "L",
            "Feature": "R",
            "profile": {
                "Api_type": "T",
                "LoginID": settings.BLUEDART_LOGIN_ID,
                "LicenceKey": settings.BLUEDART_LICENSE_KEY
            }
        }

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Serviceability Check Failed: {res.text}")

            result = res.json().get("GetServicesforPincodeAndProductResult", {})
            return {
                "pincode": result.get("PinCode"),
                "area_name": result.get("PinDescription"),
                "delivery_available": result.get("DeliveryService") == "Yes",
                "pickup_available": result.get("PickupService") == "Yes",
                "delivery_area_code": result.get("DeliveryAreaCode"),
                "pickup_area_code": result.get("PickupAreaCode"),
                "service_name": result.get("ServiceName"),
                "error_message": result.get("ErrorMessage")
            }

    @classmethod
    async def generate_waybill(cls, order, address) -> dict:
        """Generates a Blue Dart AWB / Waybill for a confirmed order."""
        token = await cls.get_jwt_token()
        url = f"{settings.BLUEDART_BASE_URL}/in/transportation/waybill/v1/GenerateWayBill"

        headers = {
            "JWTToken": token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Calculate package dimensions and items
        item_details = []
        total_weight = 0.0
        total_quantity = 0

        for item in order.items:
            product = item.product
            item_weight = float(product.weight) if product and product.weight else 0.5
            total_weight += item_weight * item.quantity
            total_quantity += item.quantity

            item_details.append({
                "ItemID": str(item.product_id)[:10],
                "ItemName": item.product_name[:30],
                "ItemValue": float(item.price),
                "Itemquantity": item.quantity,
                "InvoiceNumber": order.order_number,
                "InvoiceDate": f"/Date({int(time.time() * 1000)})/",
                "SellerName": "SURGICAL WORLD",
                "TaxableAmount": float(item.total),
                "CGSTAmount": 0,
                "SGSTAmount": 0,
                "IGSTAmount": 0,
                "TotalValue": float(item.total),
                "SKUNumber": item.product_sku[:10] if item.product_sku else "SKU001",
                "countryOfOrigin": "IN",
                "ProductDesc1": "Medical/Surgical Product"
            })

        # Base Payload Setup
        payload = {
            "Request": {
                "Consignee": {
                    "ConsigneeName": address.full_name[:30],
                    "ConsigneeMobile": address.phone,
                    "ConsigneeEmailID": address.email or "customer@surgicalworld.org",
                    "ConsigneeAddress1": address.address_line1[:30],
                    "ConsigneeAddress2": (address.address_line2 or "")[:30],
                    "ConsigneeAddress3": (address.city or "")[:30],
                    "ConsigneePincode": address.pincode
                },
                "Returnadds": {
                    "ReturnAddress1": "SURGICAL WORLD",
                    "ReturnAddress2": "SR Nagar",
                    "ReturnAddress3": "Hyderabad",
                    "ReturnContact": "SURGICAL WORLD",
                    "ReturnEmailID": "support@surgicalworld.com",
                    "ReturnMobile": "9876543210",
                    "ReturnPincode": "500038"
                },
                "Services": {
                    "ActualWeight": f"{max(0.5, total_weight):.2f}",
                    "CollectableAmount": float(order.total_amount) if order.payment_method == "cod" else 0,
                    "Commodity": {"CommodityDetail1": "Surgical Supplies"},
                    "CreditReferenceNo": order.order_number,
                    "DeclaredValue": float(order.subtotal),
                    "Dimensions": [{
                        "Length": 30,
                        "Breadth": 20,
                        "Height": 10,
                        "Count": 1
                    }],
                    "ItemCount": len(order.items),
                    "PackType": "L",
                    "PickupDate": f"/Date({int(time.time() * 1000)})/",
                    "PickupTime": "1600",
                    "PieceCount": "1",
                    "ProductCode": settings.BLUEDART_DEFAULT_PRODUCT,
                    "SubProductCode": settings.BLUEDART_DEFAULT_SUBPRODUCT,
                    "ProductType": 1,
                    "RegisterPickup": True,
                    "itemdtl": item_details
                },
                "Shipper": {
                    "CustomerCode": settings.BLUEDART_CUSTOMER_CODE,
                    "CustomerName": "SURGICAL WORLD",
                    "CustomerMobile": "9876543210",
                    "CustomerEmailID": "support@surgicalworld.com",
                    "CustomerAddress1": "SR Nagar",
                    "CustomerAddress2": "Hyderabad",
                    "CustomerAddress3": "Telangana",
                    "CustomerPincode": "500038",
                    "IsToPayCustomer": True,
                    "OriginArea": settings.BLUEDART_ORIGIN_AREA,
                    "Sender": "SURGICAL WORLD"
                }
            },
            "Profile": {
                "LoginID": settings.BLUEDART_LOGIN_ID,
                "LicenceKey": settings.BLUEDART_LICENSE_KEY,
                "Api_type": "S"
            }
        }

        async with httpx.AsyncClient(timeout=60) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Waybill Generation Failed: {res.text}")

            res_data = res.json().get("GenerateWayBillResult", {})
            if res_data.get("IsError"):
                status_info = res_data.get("Status", [{}])[0].get("StatusInformation")
                raise HTTPException(status_code=400, detail=f"Blue Dart Error: {status_info}")

            # Extract Token Number from Status list
            token_number = None
            for st in res_data.get("Status", []):
                if "Pickup Registration" in st.get("StatusCode", ""):
                    token_number = st.get("StatusInformation")

            return {
                "awb_number": res_data.get("AWBNo"),
                "pickup_token_number": token_number or res_data.get("TokenNumber"),
                "cluster_code": res_data.get("ClusterCode"),
                "destination_area": res_data.get("DestinationArea"),
                "destination_location": res_data.get("DestinationLocation"),
                "mps_details": res_data.get("MPSDetails")
            }

    @classmethod
    async def track_shipment(cls, awb_number: str) -> dict:
        """Fetches live shipment scans via Blue Dart XML Tracking API."""
        token = await cls.get_jwt_token()
        url = f"{settings.BLUEDART_BASE_URL}/in/transportation/tracking/v1/shipment"

        headers = {
            "JWTToken": token,
            "Accept": "application/xml"
        }

        params = {
            "handler": "tnt",
            "action": "custawbquery",
            "loginid": settings.BLUEDART_LOGIN_ID,
            "awb": "awb",
            "numbers": awb_number,
            "format": "xml",
            "lickey": settings.BLUEDART_LICENSE_KEY,
            "verno": "1",
            "scan": "1"
        }

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(url, headers=headers, params=params)
            if res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Tracking Request Failed: {res.text}")

            # Parse XML Response
            root = ET.fromstring(res.text)
            shipment = root.find("Shipment")

            if shipment is None:
                return {"status": "Unknown", "scans": []}

            status = shipment.findtext("Status", default="PICKUP HAS BEEN REGISTERED")
            origin = shipment.findtext("Origin", default="")
            destination = shipment.findtext("Destination", default="")

            scans = []
            scans_node = shipment.find("Scans")
            if scans_node is not None:
                for scan_detail in scans_node.findall("ScanDetail"):
                    scan_text = scan_detail.findtext("Scan", "").strip()
                    scan_code = scan_detail.findtext("ScanCode", "")
                    scan_type = scan_detail.findtext("ScanType", "")
                    scan_group_type = scan_detail.findtext("ScanGroupType", "")
                    scan_date = scan_detail.findtext("ScanDate", "")
                    scan_time = scan_detail.findtext("ScanTime", "")
                    location = scan_detail.findtext("ScannedLocation", "")

                    # Parse Date string (e.g. "06-Aug-2026 17:02")
                    scanned_at = datetime.now(timezone.utc)
                    try:
                        scanned_at = datetime.strptime(f"{scan_date} {scan_time}", "%d-%b-%Y %H:%M").replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                    scans.append({
                        "scan_status": scan_text,
                        "scan_code": scan_code,
                        "scan_type": scan_type,
                        "scan_group_type": scan_group_type,
                        "scanned_location": location,
                        "scanned_at": scanned_at
                    })

            return {
                "awb_number": awb_number,
                "status": status,
                "origin": origin,
                "destination": destination,
                "scans": scans
            }