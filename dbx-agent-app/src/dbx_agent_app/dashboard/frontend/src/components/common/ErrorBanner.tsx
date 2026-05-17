interface Props {
  message: string;
}

export function ErrorBanner({ message }: Props) {
  return <div className="error-banner">{message}</div>;
}
