import AdminConsole, { type AdminPageProps } from '../../components/AdminConsole';

type Props = Omit<AdminPageProps, 'section'>;

export default function AdminInvoicesPage(props: Props) {
  return <AdminConsole {...props} section="invoices" />;
}
