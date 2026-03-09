interface Props {
  large?: boolean;
}

export function Spinner({ large }: Props) {
  return <span className={`spinner${large ? " spinner-lg" : ""}`} />;
}
