import AdminConsole, { type AdminPageProps } from '../../components/AdminConsole';

type Props = Omit<AdminPageProps, 'section'>;

export default function AdminSubscriptionsPage(props: Props) {
  return <AdminConsole {...props} section="subscriptions" />;
}
