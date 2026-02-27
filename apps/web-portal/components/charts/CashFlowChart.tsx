import { ResponsiveLine } from '@nivo/line';

const data = [
  {
    id: 'Cash Flow',
    data: [
      { x: 'Jan', y: 2100 }, { x: 'Feb', y: 2400 }, { x: 'Mar', y: 1900 },
      { x: 'Apr', y: 3200 }, { x: 'May', y: 3800 }, { x: 'Jun', y: 3500 },
      { x: 'Jul', y: 4100 }, { x: 'Aug', y: 3900 }, { x: 'Sep', y: 4500 },
      { x: 'Oct', y: 4800 }, { x: 'Nov', y: 5200 }, { x: 'Dec', y: 5800 },
    ],
  },
];

export default function CashFlowChart() {
  return (
    <div style={{ height: 300 }}>
      <ResponsiveLine
        data={data}
        margin={{ top: 20, right: 20, bottom: 40, left: 60 }}
        xScale={{ type: 'point' }}
        yScale={{ type: 'linear', min: 0, max: 'auto' }}
        curve="monotoneX"
        enableArea={true}
        areaOpacity={0.15}
        colors={['#14b8a6']}
        lineWidth={3}
        pointSize={8}
        pointColor="#0f172a"
        pointBorderWidth={2}
        pointBorderColor="#14b8a6"
        enableGridX={false}
        gridYValues={5}
        theme={{
          background: 'transparent',
          text: { fill: '#94a3b8', fontSize: 12 },
          grid: { line: { stroke: 'rgba(148,163,184,0.1)' } },
          crosshair: { line: { stroke: '#14b8a6' } },
          tooltip: {
            container: { background: '#1e293b', color: '#f1f5f9', borderRadius: '8px', border: '1px solid rgba(148,163,184,0.15)' }
          }
        }}
        axisBottom={{ tickSize: 0, tickPadding: 10 }}
        axisLeft={{ tickSize: 0, tickPadding: 10, format: (v) => `£${Number(v) / 1000}k` }}
        enableSlices="x"
        defs={[
          { id: 'gradientA', type: 'linearGradient', colors: [{ offset: 0, color: '#14b8a6', opacity: 0.3 }, { offset: 100, color: '#14b8a6', opacity: 0 }] }
        ]}
        fill={[{ match: '*', id: 'gradientA' }]}
      />
    </div>
  );
}
