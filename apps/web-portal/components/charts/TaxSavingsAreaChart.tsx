import { ResponsiveLine } from '@nivo/line';

const data = [
  {
    id: 'Tax Saved',
    data: [
      { x: 'Jan', y: 180 },
      { x: 'Feb', y: 320 },
      { x: 'Mar', y: 410 },
      { x: 'Apr', y: 560 },
      { x: 'May', y: 720 },
      { x: 'Jun', y: 890 },
      { x: 'Jul', y: 1050 },
      { x: 'Aug', y: 1230 },
      { x: 'Sep', y: 1430 },
      { x: 'Oct', y: 1650 },
      { x: 'Nov', y: 1840 },
      { x: 'Dec', y: 2080 },
    ],
  },
];

export default function TaxSavingsAreaChart() {
  return (
    <div style={{ height: 300 }}>
      <ResponsiveLine
        data={data}
        margin={{ top: 20, right: 20, bottom: 40, left: 65 }}
        xScale={{ type: 'point' }}
        yScale={{ type: 'linear', min: 0, max: 'auto' }}
        curve="monotoneX"
        enableArea={true}
        areaOpacity={0.2}
        colors={['#d97706']}
        lineWidth={3}
        pointSize={8}
        pointColor="#0f172a"
        pointBorderWidth={2}
        pointBorderColor="#d97706"
        enableGridX={false}
        gridYValues={5}
        theme={{
          background: 'transparent',
          text: { fill: '#94a3b8', fontSize: 12 },
          grid: { line: { stroke: 'rgba(148,163,184,0.1)' } },
          crosshair: { line: { stroke: '#d97706' } },
          tooltip: {
            container: {
              background: '#1e293b',
              color: '#f1f5f9',
              borderRadius: '8px',
              border: '1px solid rgba(148,163,184,0.15)',
            },
          },
        }}
        axisBottom={{ tickSize: 0, tickPadding: 10 }}
        axisLeft={{
          tickSize: 0,
          tickPadding: 10,
          format: (v) => `£${v}`,
        }}
        enableSlices="x"
        defs={[
          {
            id: 'gradientGold',
            type: 'linearGradient',
            colors: [
              { offset: 0, color: '#d97706', opacity: 0.35 },
              { offset: 100, color: '#d97706', opacity: 0 },
            ],
          },
        ]}
        fill={[{ match: '*', id: 'gradientGold' }]}
      />
    </div>
  );
}
