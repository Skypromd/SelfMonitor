import AdminConsole, { type AdminPageProps } from '../../components/AdminConsole';

type Props = Omit<AdminPageProps, 'section'>;

export default function AdminAiAgentPage(props: Props) {
  return <AdminConsole {...props} section="ai-agent" />;
}
