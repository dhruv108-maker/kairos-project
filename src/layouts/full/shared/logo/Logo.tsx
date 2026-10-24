import { Link } from "react-router";
import LogoIcon from "src/assets/images/logos/logoicon.svg";

const Logo = () => (
  <Link
    to="/"
    aria-label="Kairos home"
    className="inline-flex items-center gap-2 rounded-md p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
  >
    <img src={LogoIcon} alt="" aria-hidden="true" className="size-8" />
  </Link>
);

export default Logo;
