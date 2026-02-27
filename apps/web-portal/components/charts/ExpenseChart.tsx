import { ResponsiveBar } from '@nivo/bar';

const data = [
  { category: 'Software', amount: 2400 },
  { category: 'Travel', amount: 1800 },
  { category: 'Office', amount: 1200 },
  { category: 'Marketing', amount: 950 },
  { category: 'Insurance', amount: 720 },
  { category: 'Training', amount: 480 },
];

export default function ExpenseChart() {
  return (
    <div style={{ height: 280 }}>
      <ResponsiveBar
        data={data}
        keys={['amount']}
        indexBy="category"
        layout="horizontal"
        margin={{ top: 10, right: 40, bottom: 10, left: 80 }}
        padding={0.35}
        colors={['#14b8a6']}
        borderRadius={6}
        enableGridY={false}
        enableGridX={false}
        axisTop={null}
        axisRight={null}
        axisBottom={null}
        axisLeft={{ tickSize: 0, tickPadding: 10 }}
        labelFormat={(v) => `£${v}`}
        labelTextColor="#0f172a"
        theme={{
          background: 'transparent',
          text: { fill: '#94a3b8', fontSize: 13 },
          tooltip: {
            container: { background: '#1e293b', color: '#f1f5f9', borderRadius: '8px', border: '1px solid rgba(148,163,184,0.15)' }
          }
        }}
      />
    </div>
  );
}
