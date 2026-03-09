interface Props {
  title: string;
  message?: string;
}

export function EmptyState({ title, message }: Props) {
  return (
    <div className="empty-state">
      <h2>{title}</h2>
      {message && <p>{message}</p>}
    </div>
  );
}
