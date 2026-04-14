import AdminConsole, { type AdminPageProps } from '../../components/AdminConsole';

type Props = Omit<AdminPageProps, 'section'>;

export default function AdminHealthPage(props: Props) {
  return <AdminConsole {...props} section="health" />;
}
