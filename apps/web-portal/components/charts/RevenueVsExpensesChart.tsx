import { ResponsiveBar } from '@nivo/bar';

const data = [
  { month: 'Jan', Revenue: 3200, Expenses: 1100 },
  { month: 'Feb', Revenue: 3800, Expenses: 1300 },
  { month: 'Mar', Revenue: 2900, Expenses: 1050 },
  { month: 'Apr', Revenue: 4500, Expenses: 1400 },
  { month: 'May', Revenue: 5100, Expenses: 1600 },
  { month: 'Jun', Revenue: 4800, Expenses: 1550 },
  { month: 'Jul', Revenue: 5600, Expenses: 1700 },
  { month: 'Aug', Revenue: 5200, Expenses: 1800 },
  { month: 'Sep', Revenue: 6100, Expenses: 1900 },
  { month: 'Oct', Revenue: 6500, Expenses: 2100 },
  { month: 'Nov', Revenue: 7200, Expenses: 2200 },
  { month: 'Dec', Revenue: 7800, Expenses: 2400 },
];

export default function RevenueVsExpensesChart() {
  return (
    <div style={{ height: 300 }}>
      <ResponsiveBar
        data={data}
        keys={['Revenue', 'Expenses']}
        indexBy="month"
        groupMode="grouped"
        margin={{ top: 20, right: 30, bottom: 40, left: 60 }}
        padding={0.3}
        innerPadding={3}
        colors={['#14b8a6', '#f87171']}
        borderRadius={4}
        enableGridX={false}
        gridYValues={5}
        axisBottom={{ tickSize: 0, tickPadding: 8 }}
        axisLeft={{ tickSize: 0, tickPadding: 8, format: (v) => `£${Number(v) / 1000}k` }}
        enableLabel={false}
        legends={[
          {
            dataFrom: 'keys',
            anchor: 'top-right',
            direction: 'row',
            itemWidth: 90,
            itemHeight: 20,
            symbolSize: 10,
            symbolShape: 'circle',
          },
        ]}
        theme={{
          background: 'transparent',
          text: { fill: '#94a3b8', fontSize: 12 },
          grid: { line: { stroke: 'rgba(148,163,184,0.1)' } },
          legends: { text: { fill: '#94a3b8', fontSize: 12 } },
          tooltip: {
            container: {
              background: '#1e293b',
              color: '#f1f5f9',
              borderRadius: '8px',
              border: '1px solid rgba(148,163,184,0.15)',
            },
          },
        }}
      />
    </div>
  );
}
