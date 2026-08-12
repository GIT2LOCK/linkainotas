interface ToggleRowProps {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}

export function ToggleRow({ checked, label, onChange }: ToggleRowProps) {
  return (
    <label className="toggle-row">
      <input
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <span>{label}</span>
    </label>
  );
}
