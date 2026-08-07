# app/services/customer/shipping_service.py
import xml.etree.ElementTree as ET
from app.services.integrations.bluedart_client import bluedart_client
from app.schemas.store.shipping_schema import ServiceabilityResponse, TransitTimeResponse

class CustomerShippingService:
    @staticmethod
    async def check_pincode_serviceability(pincode: str) -> ServiceabilityResponse:
        """Call Blue Dart Location Finder API."""
        payload = {
            "pinCode": pincode,
            "Profile": bluedart_client.get_profile_object()
        }
        
        res = await bluedart_client.request_json(
            "/in/transportation/finder/v1/GetServicesforPincode", payload
        )
        
        service_details = res.get("ServiceCenterDetailsReference", {})
        is_error = res.get("IsError", False) or service_details.get("IsError", False)
        
        if is_error:
            return ServiceabilityResponse(
                pincode=pincode,
                is_serviceable=False,
                cod_available=False,
                prepaid_available=False,
                message=service_details.get("ErrorMessage", "Pincode not serviceable")
            )

        cod_air = service_details.get("eTailCODAirInbound") == "Y"
        cod_ground = service_details.get("eTailCODGroundInbound") == "Y"
        prepaid_air = service_details.get("eTailPrePaidAirInbound") == "Y"
        prepaid_ground = service_details.get("eTailPrePaidGroundInbound") == "Y"

        return ServiceabilityResponse(
            pincode=pincode,
            is_serviceable=True,
            cod_available=(cod_air or cod_ground),
            prepaid_available=(prepaid_air or prepaid_ground),
            message="Pincode is serviceable"
        )

    @staticmethod
    async def get_transit_time(origin: str, destination: str, date_str: str, time_str: str) -> TransitTimeResponse:
        """Calculate EDD using Transit Time API."""
        payload = {
            "pPinCode": origin,
            "pPinCodeTo": destination,
            "pProductCode": "A",
            "pSubProductCode": "P",
            "pPudate": date_str.replace("-", ""),
            "pPickupTime": time_str.replace(":", ""),
            "profile": bluedart_client.get_profile_object()
        }

        res = await bluedart_client.request_json(
            "/in/transportation/transittime/v1/GetDomesticTransitTimeForPinCodeandProduct", payload
        )
        transit_ref = res.get("DomesticTranistTimeReference", {})
        
        return TransitTimeResponse(
            expected_delivery_date=transit_ref.get("ExpectedDateDelivery"),
            is_error=res.get("IsError", False),
            error_message=transit_ref.get("ErrorMessage")
        )

    @staticmethod
    async def track_shipment(awb: str, scan_history: bool = False):
        """Parse raw XML tracking data into JSON."""
        xml_str = await bluedart_client.get_tracking_xml(awb, scan_history)
        root = ET.fromstring(xml_str)
        
        shipment = root.find("Shipment")
        if shipment is None:
            return {"error": "Shipment tracking info not found"}

        status = shipment.findtext("Status")
        scans = []
        
        scans_node = shipment.find("Scans")
        if scans_node is not None:
            for scan in scans_node.findall("ScanDetail"):
                scans.append({
                    "scan": scan.findtext("Scan"),
                    "scan_code": scan.findtext("ScanCode"),
                    "date": scan.findtext("ScanDate"),
                    "time": scan.findtext("ScanTime"),
                    "location": scan.findtext("ScannedLocation")
                })

        return {
            "waybill_no": shipment.attrib.get("WaybillNo"),
            "status": status,
            "expected_delivery": shipment.findtext("ExpectedDeliveryDate"),
            "scans": scans
        }