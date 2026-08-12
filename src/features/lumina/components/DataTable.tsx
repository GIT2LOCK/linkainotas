import type { ReactNode } from "react";

export interface DataTableColumn {
  key: string;
  label: string;
  render?: (row: Record<string, unknown>) => ReactNode;
}

interface DataTableProps {
  columns: DataTableColumn[];
  rows: Record<string, unknown>[];
  emptyLabel: string;
}

export function DataTable({ columns, rows, emptyLabel }: DataTableProps) {
  return (
    <div className="table-shell">
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={String(column.key)}>{column.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="empty-cell" colSpan={columns.length}>
                  {emptyLabel}
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {columns.map((column) => (
                    <td data-column={column.key} key={String(column.key)}>
                      {renderCell(column, row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <div className="table-footer" aria-live="polite">
        {rows.length === 1 ? "1 registro" : `${rows.length} registros`}
      </div>
    </div>
  );
}

function renderCell(column: DataTableColumn, row: Record<string, unknown>) {
  if (column.render) {
    return column.render(row);
  }

  const value = String(row[column.key] ?? "");

  if (column.key !== "status" || !value) {
    return value;
  }

  const normalizedStatus = value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-");

  return (
    <span className={`status-badge status-${normalizedStatus}`}>
      <span aria-hidden="true" />
      {value}
    </span>
  );
}
