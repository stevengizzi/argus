import type { ReactNode } from 'react';

export interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => ReactNode;
  align?: 'left' | 'right' | 'center';
  className?: string;
  hideBelow?: 'sm' | 'md' | 'lg';
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
}

const alignClasses: Record<NonNullable<Column<unknown>['align']>, string> = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
};

const hideBelowClasses: Record<NonNullable<Column<unknown>['hideBelow']>, string> = {
  sm: 'hidden sm:table-cell',
  md: 'hidden md:table-cell',
  lg: 'hidden lg:table-cell',
};

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  emptyMessage = 'No data available',
  onRowClick,
}: DataTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-argus-text-dim text-sm">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="sticky top-0 z-10">
          <tr className="bg-argus-surface-2">
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-3 py-2 text-xs font-medium uppercase tracking-wider text-argus-text-dim ${
                  alignClasses[col.align ?? 'left']
                } ${col.hideBelow ? hideBelowClasses[col.hideBelow] : ''} ${col.className ?? ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-argus-border">
          {data.map((item) => (
            <tr
              key={keyExtractor(item)}
              onClick={onRowClick ? () => onRowClick(item) : undefined}
              className={`hover:bg-argus-bg/50 transition-colors duration-150 ${
                onRowClick ? 'cursor-pointer' : ''
              }`}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={`px-3 py-2.5 text-sm tabular-nums ${
                    alignClasses[col.align ?? 'left']
                  } ${col.hideBelow ? hideBelowClasses[col.hideBelow] : ''} ${col.className ?? ''}`}
                >
                  {col.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
