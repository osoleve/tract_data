import os
import requests
from typing import List, Dict, Tuple, Optional
from datetime import datetime


def debug_api_response(data: Dict) -> None:
    """Debug function to print the structure of the API response."""
    print("=== API RESPONSE DEBUG ===")
    print(f"Response keys: {list(data.keys())}")

    if "routes" in data:
        print(f"Number of routes: {len(data['routes'])}")
        if data["routes"]:
            route = data["routes"][0]
            print(f"First route keys: {list(route.keys())}")

            if "legs" in route:
                print(f"Number of legs in first route: {len(route['legs'])}")
                if route["legs"]:
                    leg = route["legs"][0]
                    print(f"First leg keys: {list(leg.keys())}")

                    if "steps" in leg:
                        print(f"Number of steps in first leg: {len(leg['steps'])}")
                        if leg["steps"]:
                            step = leg["steps"][0]
                            print(f"First step keys: {list(step.keys())}")
    print("=== END DEBUG ===\n")


def get_transit_routes(
    start_lat: float = None,
    start_lng: float = None,
    end_lat: float = None,
    end_lng: float = None,
    start_address: str = None,
    end_address: str = None,
    departure_time: Optional[str] = None,
    alternative_routes: bool = False,
    debug: bool = False,
) -> List[Dict]:
    """
    Get public transit route between two locations using Google Maps Routes API.
    Can accept either coordinates or addresses.

    Args:
        start_lat: Starting latitude (if using coordinates)
        start_lng: Starting longitude (if using coordinates)
        end_lat: Destination latitude (if using coordinates)
        end_lng: Destination longitude (if using coordinates)
        start_address: Starting address (if using address)
        end_address: Destination address (if using address)
        departure_time: Optional departure time in format 'YYYY-MM-DD HH:MM:SS'
                       If None, uses current time
        alternative_routes: Whether to compute alternative routes
        debug: Whether to print debug information about the API response

    Returns:
        List of route legs containing step-by-step directions
    """

    # Get API key from environment variable
    api_key = os.getenv("MAPS_API_KEY")
    if not api_key:
        raise ValueError("MAPS_API_KEY environment variable not found")

    # Validate input - either coordinates or addresses must be provided
    if start_address and end_address:
        # Using addresses
        origin_location = {"address": start_address}
        destination_location = {"address": end_address}
    elif (
        start_lat is not None
        and start_lng is not None
        and end_lat is not None
        and end_lng is not None
    ):
        # Using coordinates
        origin_location = {
            "location": {"latLng": {"latitude": start_lat, "longitude": start_lng}}
        }
        destination_location = {
            "location": {"latLng": {"latitude": end_lat, "longitude": end_lng}}
        }
    else:
        raise ValueError(
            "Must provide either coordinates (start_lat, start_lng, end_lat, end_lng) or addresses (start_address, end_address)"
        )

    # Google Maps Routes API endpoint
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    # Convert departure time to RFC3339 format if provided
    departure_rfc3339 = None
    if departure_time:
        try:
            dt = datetime.strptime(departure_time, "%Y-%m-%d %H:%M:%S")
            departure_rfc3339 = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            print(
                f"Warning: Invalid departure_time format: {departure_time}. Using current time."
            )

    if not departure_rfc3339:
        departure_rfc3339 = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Request headers - simplified field mask for transit
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": ",".join(
            [
                "routes.legs.steps.transitDetails",
                "routes.legs.steps.travelMode",
                "routes.legs.steps.startLocation",
                "routes.legs.steps.endLocation",
                "routes.legs.steps.navigationInstruction",
                "routes.legs.steps.distanceMeters",
                "routes.legs.steps.staticDuration",
                "routes.legs.startLocation",
                "routes.legs.endLocation",
                "routes.legs.duration",
                "routes.legs.distanceMeters",
                "routes.duration",
                "routes.distanceMeters",
            ]
        ),  # End of field mask
    }

    # Simplified request body for transit
    request_body = {
        "origin": origin_location,
        "destination": destination_location,
        "travelMode": "TRANSIT",
        "transitPreferences": {
            "allowedTravelModes": ["BUS", "SUBWAY", "TRAIN", "LIGHT_RAIL"],
            "routingPreference": "FEWER_TRANSFERS",
        },
        "departureTime": departure_rfc3339,
        "computeAlternativeRoutes": alternative_routes,
        "languageCode": "en-US",
        "units": "METRIC",
    }

    try:
        # Make API request
        response = requests.post(url, headers=headers, json=request_body)

        # Check for detailed error information
        if response.status_code != 200:
            print(f"HTTP Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            response.raise_for_status()

        data = response.json()

        # Debug the response structure if requested
        if debug:
            debug_api_response(data)

        if "routes" not in data or len(data["routes"]) == 0:
            raise Exception("No routes found")

        # Extract route legs from all routes
        all_legs = []

        for route_idx, route in enumerate(data["routes"]):
            route_legs = []

            for leg_idx, leg in enumerate(route.get("legs", [])):
                # Safely extract location data
                start_location = None
                end_location = None

                if "startLocation" in leg and "latLng" in leg["startLocation"]:
                    start_location = leg["startLocation"]["latLng"]
                if "endLocation" in leg and "latLng" in leg["endLocation"]:
                    end_location = leg["endLocation"]["latLng"]

                leg_info = {
                    "route_index": route_idx,
                    "leg_index": leg_idx,
                    "start_location": start_location,
                    "end_location": end_location,
                    "distance_meters": leg.get("distanceMeters", 0),
                    "duration": leg.get("duration", "0s"),
                    "steps": [],
                }

                # Process each step in the leg
                for step_idx, step in enumerate(leg.get("steps", [])):
                    # Safely extract step location data
                    step_start_location = None
                    step_end_location = None

                    if "startLocation" in step and "latLng" in step["startLocation"]:
                        step_start_location = step["startLocation"]["latLng"]
                    if "endLocation" in step and "latLng" in step["endLocation"]:
                        step_end_location = step["endLocation"]["latLng"]

                    step_info = {
                        "step_index": step_idx,
                        "travel_mode": step.get("travelMode", "UNKNOWN"),
                        "start_location": step_start_location,
                        "end_location": step_end_location,
                        "distance_meters": step.get("distanceMeters", 0),
                        "duration": step.get(
                            "duration", step.get("staticDuration", "0s")
                        ),
                        "instructions": step.get("navigationInstruction", {}).get(
                            "instructions", ""
                        ),
                    }

                    # Add transit-specific information if available
                    if "transitDetails" in step:
                        transit = step["transitDetails"]
                        step_info["transit_details"] = {
                            "stop_details": transit.get("stopDetails", {}),
                            "transit_line": transit.get("transitLine", {}),
                            "departure_time": transit.get("departureTime"),
                            "arrival_time": transit.get("arrivalTime"),
                            "headsign": transit.get("headsign", ""),
                            "trip_short_text": transit.get("tripShortText", ""),
                            "stop_count": transit.get("stopCount", 0),
                        }

                    leg_info["steps"].append(step_info)

                route_legs.append(leg_info)

            all_legs.extend(route_legs)

        return all_legs

    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")
    except Exception as e:
        raise Exception(f"Error getting transit route: {e}")


def duration_to_seconds(duration_str: str) -> int:
    """Convert duration string like '123s' to seconds as integer."""
    if duration_str.endswith("s"):
        return int(duration_str[:-1])
    return 0


def get_walking_summary(legs: List[Dict]) -> List[int]:
    """
    Analyze a route and return consecutive walking times as a summary.

    Args:
        legs: List of route legs from get_transit_route()

    Returns:
        List of walking durations in seconds for each consecutive walking segment.
        For example, if route is walk1->walk2->bus->walk3, returns [walk1+walk2, walk3]
    """
    walking_segments = []
    current_walking_duration = 0

    # Iterate through all steps in all legs
    for leg in legs:
        for step in leg["steps"]:
            travel_mode = step.get("travel_mode", "UNKNOWN")
            step_duration = duration_to_seconds(step.get("duration", "0s"))

            if travel_mode == "WALK":
                # Add to current walking segment
                current_walking_duration += step_duration
            else:
                # Non-walking step - save current walking segment if it exists
                if current_walking_duration > 0:
                    walking_segments.append(current_walking_duration)
                    current_walking_duration = 0

    # Don't forget the last walking segment if route ends with walking
    if current_walking_duration > 0:
        walking_segments.append(current_walking_duration)

    return walking_segments


def format_walking_summary(walking_segments: List[int]) -> str:
    """Format walking segments into a readable string."""
    if not walking_segments:
        return "No walking required"

    formatted_segments = []
    for i, duration in enumerate(walking_segments, 1):
        formatted_duration = format_duration(f"{duration}s")
        formatted_segments.append(f"Walk {i}: {formatted_duration}")

    return " | ".join(formatted_segments)


def format_duration(duration_str: str) -> str:
    """Convert duration string like '123s' to human readable format."""
    if duration_str.endswith("s"):
        seconds = int(duration_str[:-1])
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minutes"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    return duration_str


def format_distance(distance_meters: int) -> str:
    """Convert distance in meters to human readable format."""
    if distance_meters < 1000:
        return f"{distance_meters} m"
    else:
        km = distance_meters / 1000
        return f"{km:.1f} km"


def print_route_summary(routes: List[Dict]) -> None:
    """Print a human-readable summary of the routes."""

    if not routes:
        print("No routes found.")
        return

    for route_index, route in enumerate(routes):
        print(f"\n=== ROUTE {route_index + 1} ===")
        print(
            f"Total distance: {format_distance(route['distance_meters'])}, "
            f"Duration: {format_duration(route['duration'])}"
        )

        for step in route["steps"]:
            distance_text = format_distance(step["distance_meters"])
            duration_text = format_duration(step["duration"])

            print(
                f"  Step {step['step_index'] + 1} ({step['travel_mode']}): "
                f"{distance_text}, {duration_text}"
            )

            if step.get("instructions"):
                print(f"    Instructions: {step['instructions']}")

            if "transit_details" in step:
                transit = step["transit_details"]

                # Transit line info
                line_info = transit.get("transit_line", {})
                line_name = (
                    line_info.get("nameShort")
                    or line_info.get("name")
                    or "Unknown Line"
                )

                # Stop info
                stop_details = transit.get("stop_details", {})
                dep_stop = stop_details.get("departureStop", {})
                arr_stop = stop_details.get("arrivalStop", {})
                dep_stop_name = dep_stop.get("name", "Unknown")
                arr_stop_name = arr_stop.get("name", "Unknown")

                print(f"    Transit: {line_name}")
                print(f"    From: {dep_stop_name} → To: {arr_stop_name}")

                # Times - handle both string and object formats
                dep_time = transit.get("departure_time")
                arr_time = transit.get("arrival_time")

                if isinstance(dep_time, dict):
                    dep_time_text = dep_time.get("text", "Unknown")
                else:
                    dep_time_text = str(dep_time) if dep_time else "Unknown"

                if isinstance(arr_time, dict):
                    arr_time_text = arr_time.get("text", "Unknown")
                else:
                    arr_time_text = str(arr_time) if arr_time else "Unknown"

                print(f"    Departure: {dep_time_text}, Arrival: {arr_time_text}")

                if transit.get("stop_count"):
                    print(f"    Stops: {transit['stop_count']}")


# Example usage
if __name__ == "__main__":
    # Example using addresses
    start_address = "100 N Greene St, Greensboro, NC 27401"
    end_address = "1002 S Elm St, Greensboro, NC 27406"

    try:
        # Get transit route using addresses
        routes = get_transit_routes(
            start_address=start_address,
            end_address=end_address,
            alternative_routes=False,
            debug=False,
            departure_time="2025-06-01 13:00:00",
        )

        # Print summary
        print_route_summary(routes)

        # Get walking summary for each route
        for route_index, route in enumerate(routes):
            walking_segments = get_walking_summary([route])
            print(
                f"\nWalking Summary, Route {route_index + 1}: {format_walking_summary(walking_segments)}"
            )

    except Exception as e:
        print(f"Error: {e}")
