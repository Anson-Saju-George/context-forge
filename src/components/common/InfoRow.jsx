function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-zinc-800 pb-3 last:border-0 last:pb-0">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="font-medium text-zinc-100">{value}</dd>
    </div>
  )
}

export default InfoRow
