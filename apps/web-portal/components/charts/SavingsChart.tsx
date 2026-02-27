import { ResponsivePie } from '@nivo/pie';

const data = [
  { id: 'Identified Deductions', value: 1200, color: '#14b8a6' },
  { id: 'Optimized Categories', value: 480, color: '#0d9488' },
  { id: 'Automated Filing', value: 320, color: '#d97706' },
];

export default function SavingsChart() {
  return (
    <div style={{ height: 260 }}>
      <ResponsivePie
        data={data}
        margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
        innerRadius={0.6}
        padAngle={2}
        cornerRadius={6}
        colors={['#14b8a6', '#0d9488', '#d97706']}
        borderWidth={0}
        enableArcLabels={false}
        arcLinkLabelsColor="#94a3b8"
        arcLinkLabelsTextColor="#f1f5f9"
        arcLinkLabelsThickness={2}
        arcLinkLabelsDiagonalLength={12}
        arcLinkLabelsStraightLength={8}
        theme={{
          background: 'transparent',
          text: { fill: '#f1f5f9', fontSize: 12 },
          tooltip: {
            container: { background: '#1e293b', color: '#f1f5f9', borderRadius: '8px', border: '1px solid rgba(148,163,184,0.15)' }
          }
        }}
      />
    </div>
  );
}
