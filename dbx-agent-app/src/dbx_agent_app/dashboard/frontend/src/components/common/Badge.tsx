interface Props {
  label: string;
  variant?: "blue" | "green" | "red";
}

export function Badge({ label, variant = "blue" }: Props) {
  return <span className={`badge badge-${variant}`}>{label}</span>;
}
