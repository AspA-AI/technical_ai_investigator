interface PlaceholderCardProps {
  title: string;
  description: string;
}

export function PlaceholderCard({ title, description }: PlaceholderCardProps) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/50 p-6">
      <h2 className="text-lg font-medium text-slate-200">{title}</h2>
      <p className="mt-2 text-sm text-slate-500">{description}</p>
    </div>
  );
}
