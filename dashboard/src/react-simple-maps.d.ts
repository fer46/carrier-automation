declare module 'react-simple-maps' {
  import type { ComponentType, ReactNode } from 'react';

  interface ProjectionConfig {
    rotate?: [number, number, number];
    center?: [number, number];
    scale?: number;
  }

  interface ComposableMapProps {
    projection?: string;
    projectionConfig?: ProjectionConfig;
    width?: number;
    height?: number;
    children?: ReactNode;
    style?: React.CSSProperties;
    className?: string;
  }

  interface GeographiesChildrenArgs {
    geographies: GeographyType[];
  }

  interface GeographiesProps {
    geography: string;
    children: (args: GeographiesChildrenArgs) => ReactNode;
  }

  interface GeographyType {
    rsmKey: string;
    [key: string]: unknown;
  }

  interface GeographyProps {
    geography: GeographyType;
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
    style?: {
      default?: React.CSSProperties;
      hover?: React.CSSProperties;
      pressed?: React.CSSProperties;
    };
  }

  interface MarkerProps {
    coordinates: [number, number];
    children?: ReactNode;
    onMouseEnter?: (event: React.MouseEvent) => void;
    onMouseLeave?: (event: React.MouseEvent) => void;
  }

  interface LineProps {
    from?: [number, number];
    to?: [number, number];
    coordinates?: [number, number][];
    stroke?: string;
    strokeWidth?: number;
    strokeLinecap?: string;
    strokeDasharray?: string;
    strokeOpacity?: number;
    fill?: string;
    className?: string;
    style?: React.CSSProperties;
  }

  interface ZoomableGroupProps {
    center?: [number, number];
    zoom?: number;
    minZoom?: number;
    maxZoom?: number;
    translateExtent?: [[number, number], [number, number]];
    filterZoomEvent?: (event: Event) => boolean;
    onMoveStart?: (position: { coordinates: [number, number]; zoom: number }) => void;
    onMove?: (position: { coordinates: [number, number]; zoom: number }) => void;
    onMoveEnd?: (position: { coordinates: [number, number]; zoom: number }) => void;
    children?: ReactNode;
    className?: string;
  }

  export const ComposableMap: ComponentType<ComposableMapProps>;
  export const Geographies: ComponentType<GeographiesProps>;
  export const Geography: ComponentType<GeographyProps>;
  export const Marker: ComponentType<MarkerProps>;
  export const Line: ComponentType<LineProps>;
  export const ZoomableGroup: ComponentType<ZoomableGroupProps>;
}
