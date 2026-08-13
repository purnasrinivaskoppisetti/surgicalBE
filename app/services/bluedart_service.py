# app/services/bluedart_service.py

import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.models.models import StoreSetting


class BlueDartService:

    _jwt_token: str | None = None
    _token_expiry: float = 0

    # ============================================================
    # JWT TOKEN
    # ============================================================

    @classmethod
    async def get_jwt_token(cls) -> str:
        """
        Get Blue Dart JWT token.

        Token is cached until it is close to expiry.
        """

        current_time = time.time()

        # Reuse existing token if it has more than 60 seconds remaining
        if (
            cls._jwt_token
            and cls._token_expiry - current_time > 60
        ):
            return cls._jwt_token

        headers = {
            "ClientID": settings.BLUEDART_CLIENT_ID,
            "clientSecret": settings.BLUEDART_CLIENT_SECRET,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=settings.BLUEDART_TIMEOUT_MS / 1000
            ) as client:

                response = await client.get(
                    settings.BLUEDART_AUTH_URL,
                    headers=headers,
                )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Blue Dart authentication request failed: {str(exc)}",
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Blue Dart Auth Failed: {response.text}",
            )

        try:
            data = response.json()
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="Blue Dart authentication returned invalid JSON.",
            )

        token = data.get("JWTToken") or data.get("token")

        if not token:
            raise HTTPException(
                status_code=502,
                detail="Blue Dart authentication response did not contain JWT token.",
            )

        cls._jwt_token = token

        # Keep a small safety margin.
        cls._token_expiry = current_time + 3500

        return cls._jwt_token

    # ============================================================
    # TRANSIT TIME
    # ============================================================

    @classmethod
    async def get_transit_time(
        cls,
        destination_pincode: str,
        origin_pincode: str | None = None,
        product_code: str = settings.BLUEDART_DEFAULT_PRODUCT,
        sub_product_code: str = settings.BLUEDART_DEFAULT_SUBPRODUCT,
        pickup_time: str = "16:00",
    ) -> dict:

        # ============================================================
        # 1. GET JWT TOKEN
        # ============================================================

        token = await cls.get_jwt_token()

        # ============================================================
        # 2. BLUE DART TRANSIT TIME URL
        # ============================================================

        url = (
            f"{settings.BLUEDART_BASE_URL}"
            "/in/transportation/transit/v1/"
            "GetDomesticTransitTimeForPinCodeandProduct"
        )

        # ============================================================
        # 3. PINCODES
        # ============================================================

        origin = (
            origin_pincode
            or settings.BLUEDART_ORIGIN_PINCODE
        )

        origin = str(origin).strip()
        destination_pincode = str(
            destination_pincode
        ).strip()

        # ============================================================
        # 4. VALIDATE ORIGIN PINCODE
        # ============================================================

        if not origin.isdigit() or len(origin) != 6:

            raise HTTPException(
                status_code=400,
                detail=f"Invalid origin pincode: {origin}",
            )

        # ============================================================
        # 5. VALIDATE DESTINATION PINCODE
        # ============================================================

        if (
            not destination_pincode.isdigit()
            or len(destination_pincode) != 6
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid destination pincode: "
                    f"{destination_pincode}"
                ),
            )

        # ============================================================
        # 6. NORMALIZE PICKUP TIME
        # ============================================================

        pickup_time = str(
            pickup_time
        ).strip()

        if (
            len(pickup_time) == 4
            and pickup_time.isdigit()
        ):

            pickup_time = (
                pickup_time[:2]
                + ":"
                + pickup_time[2:]
            )

        # ============================================================
        # 7. HEADERS
        # ============================================================

        headers = {
            "JWTToken": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # ============================================================
        # 8. BLUE DART PICKUP DATE
        # ============================================================

        current_millis = int(
            time.time() * 1000
        )

        p_pudate = (
            f"/Date({current_millis})/"
        )

        # ============================================================
        # 9. PAYLOAD
        # ============================================================

        payload = {
            "pPinCodeFrom": origin,
            "pPinCodeTo": destination_pincode,
            "pProductCode": product_code,
            "pSubProductCode": sub_product_code,
            "pPudate": p_pudate,
            "pPickupTime": pickup_time,

            "profile": {
                "LoginID": settings.BLUEDART_LOGIN_ID,
                "LicenceKey": settings.BLUEDART_LICENSE_KEY,
                "Api_type": "S",
            },
        }

        # ============================================================
        # 10. CALL BLUE DART
        # ============================================================

        try:

            async with httpx.AsyncClient(
                timeout=30
            ) as client:

                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

        except httpx.RequestError as exc:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Blue Dart Transit API request failed: "
                    f"{str(exc)}"
                ),
            )

        # ============================================================
        # 11. HTTP RESPONSE CHECK
        # ============================================================

        if response.status_code != 200:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Transit Time API Failed: "
                    f"{response.text}"
                ),
            )

        # ============================================================
        # 12. PARSE RESPONSE
        # ============================================================

        try:

            response_json = response.json()

        except Exception:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Invalid JSON response from "
                    "Blue Dart Transit API."
                ),
            )

        # ============================================================
        # 13. GET BLUE DART RESULT
        # ============================================================

        result = response_json.get(
            "GetDomesticTransitTimeForPinCodeandProductResult",
            {},
        )

        # ============================================================
        # 14. FALLBACK RESPONSE KEY
        # ============================================================

        if not result:

            result = response_json.get(
                "GetDomesticTransitTimeForPinCodeandProduct",
                {},
            )

        # ============================================================
        # 15. EMPTY RESPONSE
        # ============================================================

        if not result:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Blue Dart returned an empty "
                    "Transit Time response."
                ),
            )

        # ============================================================
        # 16. BLUE DART ERROR
        # ============================================================

        if result.get("IsError"):

            return {
                "is_serviceable": False,

                "origin_pincode": origin,

                "destination_pincode":
                    destination_pincode,

                "expected_delivery_date": None,

                "expected_pod_date": None,

                "delivery_area_code":
                    result.get("Area"),

                "service_center":
                    result.get("ServiceCenter"),

                "additional_days":
                    result.get(
                        "AdditionalDays",
                        "0",
                    ),

                "apex_additional_days":
                    result.get(
                        "ApexAdditionalDays",
                        "0",
                    ),

                "ground_additional_days":
                    result.get(
                        "GroundAdditionalDays",
                        "0",
                    ),

                "edl_message":
                    result.get("EDLMessage"),

                "message":
                    result.get(
                        "ErrorMessage",
                        "Transit time unavailable.",
                    ),
            }

        # ============================================================
        # 17. SUCCESS RESPONSE
        # ============================================================

        return {
            "is_serviceable": True,

            "origin_pincode": origin,

            "destination_pincode":
                destination_pincode,

            "expected_delivery_date":
                result.get(
                    "ExpectedDateDelivery"
                ),

            "expected_pod_date":
                result.get(
                    "ExpectedDatePOD"
                ),

            "delivery_area_code":
                result.get(
                    "Area"
                ),

            "service_center":
                result.get(
                    "ServiceCenter"
                ),

            "additional_days":
                result.get(
                    "AdditionalDays",
                    "0",
                ),

            "apex_additional_days":
                result.get(
                    "ApexAdditionalDays",
                    "0",
                ),

            "ground_additional_days":
                result.get(
                    "GroundAdditionalDays",
                    "0",
                ),

            "edl_message":
                result.get(
                    "EDLMessage"
                ),

            "message":
                result.get(
                    "ErrorMessage"
                )
                or "Transit time calculated successfully.",
        }
    # ============================================================
    # SERVICEABILITY
    # ============================================================

    @classmethod
    async def check_serviceability(
        cls,
        pincode: str,
        product_code: str = settings.BLUEDART_DEFAULT_PRODUCT,
        sub_product_code: str = settings.BLUEDART_DEFAULT_SUBPRODUCT,
    ) -> dict:

        token = await cls.get_jwt_token()

        url = (
            f"{settings.BLUEDART_BASE_URL}"
            "/in/transportation/finder/v1/"
            "GetServicesforPincodeAndProduct"
        )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "JWTToken": token,
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
                "LicenceKey": settings.BLUEDART_LICENSE_KEY,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Blue Dart serviceability request failed: {str(exc)}",
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=400,
                detail=f"Serviceability Check Failed: {response.text}",
            )

        result = response.json().get(
            "GetServicesforPincodeAndProductResult",
            {},
        )

        return {
            "pincode": result.get("PinCode"),
            "area_name": result.get("PinDescription"),
            "delivery_available": (
                result.get("DeliveryService") == "Yes"
            ),
            "pickup_available": (
                result.get("PickupService") == "Yes"
            ),
            "delivery_area_code": result.get(
                "DeliveryAreaCode"
            ),
            "pickup_area_code": result.get(
                "PickupAreaCode"
            ),
            "service_name": result.get("ServiceName"),
            "error_message": result.get("ErrorMessage"),
        }

    # ============================================================
    # CALCULATE PACKAGE
    # ============================================================

    @classmethod
    def calculate_package_details(
        cls,
        order,
    ) -> dict:
        """
        Calculate shipment weight and dimensions
        from all products in the order.

        Assumption:
        ----------------
        All order items are packed into ONE package.

        Weight:
            product.weight * quantity

        Length:
            maximum product length

        Breadth:
            maximum product breadth

        Height:
            sum(product.height * quantity)

        If later you support multiple boxes/MPS,
        this calculation should be replaced by
        package-level calculations.
        """

        if not order.items:
            raise HTTPException(
                status_code=400,
                detail="Order does not contain any products.",
            )

        total_weight = Decimal("0")
        max_length = Decimal("0")
        max_breadth = Decimal("0")
        total_height = Decimal("0")

        total_quantity = 0

        item_details = []

        commodity_names = []

        for item in order.items:

            product = item.product

            if not product:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Product information missing for "
                        f"order item {item.id}."
                    ),
                )

            quantity = int(item.quantity or 0)

            if quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Invalid quantity for product "
                        f"{item.product_name}."
                    ),
                )

            # ------------------------------------------------
            # PRODUCT DIMENSIONS
            # ------------------------------------------------

            product_weight = (
                Decimal(str(product.weight))
                if product.weight is not None
                else Decimal("0.5")
            )

            product_length = (
                Decimal(str(product.length))
                if product.length is not None
                else Decimal("10")
            )

            product_breadth = (
                Decimal(str(product.breadth))
                if product.breadth is not None
                else Decimal("10")
            )

            product_height = (
                Decimal(str(product.height))
                if product.height is not None
                else Decimal("5")
            )

            # Prevent zero/negative dimensions
            product_weight = max(
                product_weight,
                Decimal("0.01"),
            )

            product_length = max(
                product_length,
                Decimal("1"),
            )

            product_breadth = max(
                product_breadth,
                Decimal("1"),
            )

            product_height = max(
                product_height,
                Decimal("1"),
            )

            # ------------------------------------------------
            # TOTALS
            # ------------------------------------------------

            total_weight += (
                product_weight * quantity
            )

            max_length = max(
                max_length,
                product_length,
            )

            max_breadth = max(
                max_breadth,
                product_breadth,
            )

            total_height += (
                product_height * quantity
            )

            total_quantity += quantity

            # ------------------------------------------------
            # COMMODITY
            # ------------------------------------------------

            category_name = "Medical Supplies"

            if product.category:
                category_name = (
                    product.category.name
                    or "Medical Supplies"
                )

            if category_name not in commodity_names:
                commodity_names.append(category_name)

            # ------------------------------------------------
            # BLUE DART ITEM DETAILS
            # ------------------------------------------------

            item_details.append(
                {
                    "ItemID": str(item.product_id)[:10],

                    "ItemName": (
                        item.product_name or product.name
                    )[:30],

                    "ItemValue": float(item.price or 0),

                    "Itemquantity": quantity,

                    "InvoiceNumber": str(
                        order.order_number
                    )[:30],

                    "InvoiceDate": (
                        f"/Date({int(time.time() * 1000)})/"
                    ),

                    "SellerName": (
                        "SURGICAL WORLD"
                    )[:30],

                    "TaxableAmount": float(
                        item.total or 0
                    ),

                    "CGSTAmount": 0,

                    "SGSTAmount": 0,

                    "IGSTAmount": 0,

                    "TotalValue": float(
                        item.total or 0
                    ),

                    "SKUNumber": (
                        item.product_sku
                        or product.sku
                        or "SKU001"
                    )[:10],

                    "countryOfOrigin": "IN",

                    "ProductDesc1": (
                        product.short_description
                        or product.name
                        or item.product_name
                        or "Medical Supplies"
                    )[:30],
                }
            )

        # ----------------------------------------------------
        # BLUE DART MINIMUM WEIGHT
        # ----------------------------------------------------

        actual_weight = max(
            total_weight,
            Decimal("0.50"),
        )

        # ----------------------------------------------------
        # MINIMUM PACKAGE DIMENSIONS
        # ----------------------------------------------------

        package_length = max(
            max_length,
            Decimal("10"),
        )

        package_breadth = max(
            max_breadth,
            Decimal("10"),
        )

        package_height = max(
            total_height,
            Decimal("5"),
        )

        commodity = (
            ", ".join(commodity_names)
            if commodity_names
            else "Surgical Supplies"
        )

        commodity = commodity[:30]

        return {
            "actual_weight": actual_weight.quantize(
                Decimal("0.01")
            ),

            "length": package_length.quantize(
                Decimal("0.01")
            ),

            "breadth": package_breadth.quantize(
                Decimal("0.01")
            ),

            "height": package_height.quantize(
                Decimal("0.01")
            ),

            "piece_count": 1,

            "total_quantity": total_quantity,

            "item_count": len(order.items),

            "commodity": commodity,

            "item_details": item_details,
        }

    # ============================================================
    # GENERATE WAYBILL
    # ============================================================

    @classmethod
    async def generate_waybill(
        cls,
        order,
        address,
        store_setting: StoreSetting | None = None,
    ) -> dict:

        token = await cls.get_jwt_token()

        url = (
            f"{settings.BLUEDART_BASE_URL}"
            "/in/transportation/waybill/v1/"
            "GenerateWayBill"
        )

        headers = {
            "JWTToken": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # ========================================================
        # STORE / SHIPPER DETAILS
        # ========================================================

        company_name = (
            store_setting.company_name
            if store_setting
            and store_setting.company_name
            else "SURGICAL WORLD"
        ).strip()

        support_email = (
            store_setting.support_email
            if store_setting
            and store_setting.support_email
            else "support@surgicalworld.org"
        ).strip()

        support_phone = (
            store_setting.support_phone
            if store_setting
            and store_setting.support_phone
            else "9876543210"
        ).strip()

        store_address_full = (
            store_setting.address
            if store_setting
            and store_setting.address
            else "Main Warehouse, Guntur, Andhra Pradesh"
        )

        addr_parts = [
            part.strip()
            for part in store_address_full.split(",")
            if part.strip()
        ]

        shipper_addr1 = (
            addr_parts[0]
            if len(addr_parts) > 0
            else "Main Warehouse"
        )[:30]

        shipper_addr2 = (
            addr_parts[1]
            if len(addr_parts) > 1
            else "Industrial Area"
        )[:30]

        shipper_addr3 = (
            addr_parts[2]
            if len(addr_parts) > 2
            else "Andhra Pradesh"
        )[:30]

        # ========================================================
        # PAYMENT / COD
        # ========================================================

        is_cod = False

        if order.payments:

            latest_payment = max(
                order.payments,
                key=lambda payment: (
                    payment.created_at
                    or datetime.min.replace(
                        tzinfo=timezone.utc
                    )
                ),
            )

            if latest_payment.payment_method:

                is_cod = (
                    str(
                        latest_payment.payment_method
                    ).lower()
                    == "paymentmethod.cod"
                    or str(
                        latest_payment.payment_method
                    ).lower()
                    == "cod"
                )

        # ========================================================
        # PACKAGE CALCULATION
        # ========================================================

        package = cls.calculate_package_details(order)

        actual_weight = package["actual_weight"]

        package_length = package["length"]

        package_breadth = package["breadth"]

        package_height = package["height"]

        piece_count = package["piece_count"]

        item_details = package["item_details"]

        commodity = package["commodity"]

        # ========================================================
        # BLUE DART PRODUCT
        # ========================================================

        product_code = (
            settings.BLUEDART_DEFAULT_PRODUCT
        )

        sub_product_code = (
            "C"
            if is_cod
            else settings.BLUEDART_DEFAULT_SUBPRODUCT
        )

        collectable_amount = (
            float(order.total_amount)
            if is_cod
            else 0.0
        )

        # ========================================================
        # PAYLOAD
        # ========================================================

        payload = {

            "Request": {

                # ------------------------------------------------
                # CONSIGNEE
                # ------------------------------------------------

                "Consignee": {

                    "ConsigneeName": (
                        address.full_name
                        or order.user.full_name
                    )[:30],

                    "ConsigneeMobile": (
                        address.phone
                    ),

                    "ConsigneeEmailID": (
                        address.email
                        or getattr(
                            order.user,
                            "email",
                            None,
                        )
                        or "customer@surgicalworld.org"
                    ),

                    "ConsigneeAddress1": (
                        address.address_line1
                        or ""
                    )[:30],

                    "ConsigneeAddress2": (
                        address.address_line2
                        or ""
                    )[:30],

                    "ConsigneeAddress3": (
                        f"{address.city}, "
                        f"{address.state}"
                    )[:30],

                    "ConsigneePincode": (
                        address.pincode
                    ),
                },

                # ------------------------------------------------
                # RETURN ADDRESS
                # ------------------------------------------------

                "Returnadds": {

                    "ReturnAddress1": (
                        company_name
                    )[:30],

                    "ReturnAddress2": (
                        shipper_addr1
                    ),

                    "ReturnAddress3": (
                        shipper_addr2
                    ),

                    "ReturnContact": (
                        company_name
                    )[:30],

                    "ReturnEmailID": (
                        support_email
                    ),

                    "ReturnMobile": (
                        support_phone
                    ),

                    "ReturnPincode": (
                        settings.BLUEDART_ORIGIN_PINCODE
                    ),
                },

                # ------------------------------------------------
                # SERVICES
                # ------------------------------------------------

                "Services": {

                    "ActualWeight": (
                        f"{float(actual_weight):.2f}"
                    ),

                    "CollectableAmount": (
                        collectable_amount
                    ),

                    "Commodity": {
                        "CommodityDetail1": commodity
                    },

                    "CreditReferenceNo": (
                        order.order_number
                    ),

                    "DeclaredValue": float(
                        order.subtotal or 0
                    ),

                    "Dimensions": [

                        {
                            "Length": float(
                                package_length
                            ),

                            "Breadth": float(
                                package_breadth
                            ),

                            "Height": float(
                                package_height
                            ),

                            "Count": 1,
                        }

                    ],

                    "ItemCount": (
                        package["item_count"]
                    ),

                    "PackType": "L",

                    "PickupDate": (
                        f"/Date({int(time.time() * 1000)})/"
                    ),

                    "PickupTime": "1600",

                    "PieceCount": str(
                        piece_count
                    ),

                    "ProductCode": product_code,

                    "SubProductCode": (
                        sub_product_code
                    ),

                    "ProductType": 1,

                    "RegisterPickup": True,

                    "itemdtl": item_details,
                },

                # ------------------------------------------------
                # SHIPPER
                # ------------------------------------------------

                "Shipper": {

                    "CustomerCode": (
                        settings.BLUEDART_CUSTOMER_CODE
                    ),

                    "CustomerName": (
                        company_name
                    )[:30],

                    "CustomerMobile": (
                        support_phone
                    ),

                    "CustomerEmailID": (
                        support_email
                    ),

                    "CustomerAddress1": (
                        shipper_addr1
                    ),

                    "CustomerAddress2": (
                        shipper_addr2
                    ),

                    "CustomerAddress3": (
                        shipper_addr3
                    ),

                    "CustomerPincode": (
                        settings.BLUEDART_ORIGIN_PINCODE
                    ),

                    "IsToPayCustomer": False,

                    "OriginArea": (
                        settings.BLUEDART_ORIGIN_AREA
                    ),

                    "Sender": (
                        company_name
                    )[:30],
                },
            },

            "Profile": {

                "LoginID": (
                    settings.BLUEDART_LOGIN_ID
                ),

                "LicenceKey": (
                    settings.BLUEDART_LICENSE_KEY
                ),

                "Api_type": "S",
            },
        }

        # ========================================================
        # CALL BLUE DART
        # ========================================================

        try:

            async with httpx.AsyncClient(
                timeout=60
            ) as client:

                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

        except httpx.RequestError as exc:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Blue Dart Waybill request failed: "
                    f"{str(exc)}"
                ),
            )

        if response.status_code != 200:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Waybill Generation Failed: "
                    f"{response.text}"
                ),
            )

        try:

            response_json = response.json()

        except Exception:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Blue Dart returned invalid JSON "
                    "for Waybill API."
                ),
            )

        result = response_json.get(
            "GenerateWayBillResult",
            {},
        )

        # ========================================================
        # BLUE DART ERROR
        # ========================================================

        if result.get("IsError"):

            status_information = (
                "Unknown Blue Dart error"
            )

            for status in result.get(
                "Status",
                [],
            ):

                if status.get(
                    "StatusInformation"
                ):

                    status_information = (
                        status.get(
                            "StatusInformation"
                        )
                    )

                    break

            raise HTTPException(
                status_code=400,
                detail=(
                    "Blue Dart Error: "
                    f"{status_information}"
                ),
            )

        # ========================================================
        # EXTRACT RESPONSE
        # ========================================================

        awb_number = result.get("AWBNo")

        pickup_token = result.get(
            "TokenNumber"
        )

        cluster_code = result.get(
            "ClusterCode"
        )

        destination_area = result.get(
            "DestinationArea"
        )

        destination_location = result.get(
            "DestinationLocation"
        )

        mps_details = result.get(
            "MPSDetails"
        )

        # Some Blue Dart responses contain pickup
        # registration inside Status array.

        for status in result.get(
            "Status",
            [],
        ):

            status_code = str(
                status.get(
                    "StatusCode",
                    ""
                )
            )

            status_information = (
                status.get(
                    "StatusInformation"
                )
            )

            if (
                "Pickup Registration"
                in status_code
            ):

                pickup_token = (
                    status_information
                    or pickup_token
                )

        if not awb_number:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Blue Dart did not return "
                    "an AWB/Waybill number."
                ),
            )

        # ========================================================
        # RETURN EVERYTHING NEEDED BY ROUTE
        # ========================================================

        return {

            "success": True,

            "awb_number": str(
                awb_number
            ),

            "pickup_token_number": (
                pickup_token
            ),

            "cluster_code": (
                cluster_code
            ),

            "destination_area": (
                destination_area
            ),

            "destination_location": (
                destination_location
            ),

            "mps_details": (
                mps_details
            ),

            "actual_weight": (
                actual_weight
            ),

            "length": (
                package_length
            ),

            "breadth": (
                package_breadth
            ),

            "height": (
                package_height
            ),

            "piece_count": (
                piece_count
            ),

            "total_quantity": (
                package["total_quantity"]
            ),

            "item_count": (
                package["item_count"]
            ),

            "product_code": (
                product_code
            ),

            "sub_product_code": (
                sub_product_code
            ),

            "pack_type": "L",

            "is_cod": is_cod,

            "collectable_amount": (
                collectable_amount
            ),

            "commodity": commodity,
        }

    # ============================================================
    # TRACK SHIPMENT
    # ============================================================

    @classmethod
    async def track_shipment(
        cls,
        awb_number: str,
    ) -> dict:

        token = await cls.get_jwt_token()

        url = (
            f"{settings.BLUEDART_BASE_URL}"
            "/in/transportation/tracking/v1/shipment"
        )

        tracking_license_key = (
            settings.BLUEDART_TRACKING_LICENSE_KEY
            or settings.BLUEDART_LICENSE_KEY
        )

        headers = {
            "JWTToken": token,
            "Accept": "application/xml",
        }

        params = {

            "handler": "tnt",

            "action": "custawbquery",

            "loginid": (
                settings.BLUEDART_LOGIN_ID
            ),

            "awb": "awb",

            "numbers": awb_number,

            "format": "xml",

            "lickey": tracking_license_key,

            "verno": "1",

            "scan": "1",
        }

        try:

            async with httpx.AsyncClient(
                timeout=30
            ) as client:

                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                )

        except httpx.RequestError as exc:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Blue Dart tracking request failed: "
                    f"{str(exc)}"
                ),
            )

        if response.status_code != 200:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Tracking Request Failed: "
                    f"{response.text}"
                ),
            )

        try:

            root = ET.fromstring(
                response.text
            )

        except ET.ParseError:

            raise HTTPException(
                status_code=502,
                detail=(
                    "Blue Dart tracking returned "
                    "invalid XML."
                ),
            )

        shipment = root.find(
            "Shipment"
        )

        if shipment is None:

            return {
                "awb_number": awb_number,
                "status": "Unknown",
                "origin": "",
                "destination": "",
                "scans": [],
            }

        status = shipment.findtext(
            "Status",
            default="PICKUP HAS BEEN REGISTERED",
        )

        origin = shipment.findtext(
            "Origin",
            default="",
        )

        destination = shipment.findtext(
            "Destination",
            default="",
        )

        scans = []

        scans_node = shipment.find(
            "Scans"
        )

        if scans_node is not None:

            for scan_detail in scans_node.findall(
                "ScanDetail"
            ):

                scan_text = (
                    scan_detail.findtext(
                        "Scan",
                        "",
                    )
                    or ""
                ).strip()

                scan_code = (
                    scan_detail.findtext(
                        "ScanCode",
                        "",
                    )
                    or ""
                )

                scan_type = (
                    scan_detail.findtext(
                        "ScanType",
                        "",
                    )
                    or ""
                )

                scan_group_type = (
                    scan_detail.findtext(
                        "ScanGroupType",
                        "",
                    )
                    or ""
                )

                scan_date = (
                    scan_detail.findtext(
                        "ScanDate",
                        "",
                    )
                    or ""
                )

                scan_time = (
                    scan_detail.findtext(
                        "ScanTime",
                        "",
                    )
                    or ""
                )

                location = (
                    scan_detail.findtext(
                        "ScannedLocation",
                        "",
                    )
                    or ""
                )

                scanned_at = datetime.now(
                    timezone.utc
                )

                try:

                    scanned_at = (
                        datetime.strptime(
                            f"{scan_date} {scan_time}",
                            "%d-%b-%Y %H:%M",
                        ).replace(
                            tzinfo=timezone.utc
                        )
                    )

                except Exception:
                    pass

                scans.append(
                    {
                        "scan_status": scan_text,
                        "scan_code": scan_code,
                        "scan_type": scan_type,
                        "scan_group_type": scan_group_type,
                        "scanned_location": location,
                        "scanned_at": scanned_at,
                    }
                )

        return {

            "awb_number": awb_number,

            "status": status,

            "origin": origin,

            "destination": destination,

            "scans": scans,
        }