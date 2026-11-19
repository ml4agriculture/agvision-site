import { useEffect, useState } from 'react';
import { formatLocalSchedule } from '../../lib/local-schedule';

interface Props { start: string; end: string }

/** Progressive enhancement: the host-time schedule and calendar links are HTML. */
export default function LocalSchedule({ start, end }: Props) {
  const [local, setLocal] = useState<ReturnType<typeof formatLocalSchedule>>(null);
  useEffect(() => {
    // Read browser preferences only after hydration, avoiding server/client mismatch.
    const { locale, timeZone } = Intl.DateTimeFormat().resolvedOptions();
    setLocal(formatLocalSchedule(start, end, locale, timeZone));
  }, [start, end]);

  return <p className="local-schedule" aria-live="polite" aria-atomic="true">
    {local ? <><strong>Your time ({local.timeZone}): </strong>{local.label}</> :
      <span>Times above use the workshop timezone.</span>}
  </p>;
}
