import type { CSSProperties, ReactElement } from "react";

export interface IridescenceProps {
  color?: string | [number, number, number];
  speed?: number;
  amplitude?: number;
  mouseReact?: boolean;
  scale?: number;
  detail?: number;
  rotation?: number;
  warp?: number;
  hueShift?: number;
  saturation?: number;
  brightness?: number;
  contrast?: number;
  stir?: number;
  sheen?: number;
  clickSwirl?: boolean;
  grain?: number;
  fade?: number;
  opacity?: number;
  resolution?: number;
  paused?: boolean;
  className?: string;
  style?: CSSProperties;
}

declare function Iridescence(props: IridescenceProps): ReactElement;
export default Iridescence;
