import { CameraFeature } from "@/types";
import { CircleMarker, Tooltip } from "react-leaflet";

interface CameraMarkerProps {
    camera: CameraFeature;
    color: string;
    onClick: (camera: CameraFeature) => void
}

export default function CameraMarker({
    camera,
    color,
    onClick
}: CameraMarkerProps) {
    const [longitude, latitude] = camera.geometry.coordinates;

    return(
        <CircleMarker
            center={[latitude, longitude]}
            radius={6}
            color={color}
            fillColor={color}
            fillOpacity={0.8}
            weight={1}
            eventHandlers={{ click: () => onClick(camera) }}
        >
            <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                {camera.properties.name}
            </Tooltip>
        </CircleMarker>
    )
}