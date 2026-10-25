import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import { Alert, Text, View } from "react-native";

import type { Order, ServiceCall } from "@rest/api-client";

import { Sheet } from "@/components/Sheet";
import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  Field,
  Loading,
  Muted,
  Screen,
  SectionLabel,
  Subtitle,
  Title,
} from "@/components/ui";
import { formatStatus } from "@/components/status";
import {
  useAcceptOrder,
  useAcknowledgeCall,
  useOrders,
  useRejectOrder,
  useServiceCalls,
} from "@/features/orders/api";
import { ApiError } from "@/lib/api";
import { elapsed, formatMoney } from "@/lib/format";
import { useNow } from "@/lib/useNow";
import { useTableNames } from "@/features/tables/api";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

const REJECT_REASONS = [
  {
    code: "SOLD_OUT",
    label: "Sold out",
    note: "One or more items have sold out for today.",
  },
  {
    code: "UNAVAILABLE",
    label: "Unavailable",
    note: "One or more items are unavailable right now.",
  },
  {
    code: "KITCHEN_CLOSED",
    label: "Kitchen closed",
    note: "The kitchen has stopped taking orders for this service.",
  },
  {
    code: "TABLE_MISMATCH",
    label: "Wrong table",
    note: "This order was sent to the wrong table. Please order again.",
  },
  {
    code: "OTHER",
    label: "Other",
    note: "",
  },
] as const;

export default function WaiterRequestsScreen() {
  const theme = useTheme();
  const c = theme.color;
  const now = useNow();

  const pending = useOrders("PENDING_CONFIRMATION");
  const calls = useServiceCalls("REQUESTED");
  const accept = useAcceptOrder();
  const acknowledge = useAcknowledgeCall();
  const reject = useRejectOrder();
  const tableName = useTableNames();

  const [rejecting, setRejecting] = useState<Order | null>(null);
  const [reasonCode, setReasonCode] = useState<string>("UNAVAILABLE");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const pendingOrders = pending.data ?? [];
  const openCalls = calls.data ?? [];

  function confirmAccept(order: Order) {
    const itemCount = order.items.reduce((total, item) => total + item.quantity, 0);
    Alert.alert(
      `Accept order for ${tableName(order.table_id)}?`,
      `${itemCount} item${itemCount === 1 ? "" : "s"} · ${formatMoney(
        order.total_minor,
        "USD"
      )}\n\nThis sends the order to the kitchen. It cannot be un-accepted.`,
      [
        { text: "Not yet", style: "cancel" },
        {
          text: "Accept order",
          onPress: () => {
            setError(null);
            setNotice(null);
            accept.mutate(order.id, {
              onSuccess: () =>
                setNotice(`Order for ${tableName(order.table_id)} sent to the kitchen.`),
              onError: (err) =>
                setError(
                  err instanceof ApiError ? err.detail : "Could not accept the order."
                ),
            });
          },
        },
      ]
    );
  }

  function openReject(order: Order) {
    setReasonCode("UNAVAILABLE");
    setNote(REJECT_REASONS.find((reason) => reason.code === "UNAVAILABLE")?.note ?? "");
    setError(null);
    setRejecting(order);
  }

  function submitReject() {
    if (!rejecting) return;
    reject.mutate(
      { orderId: rejecting.id, reasonCode, note: note.trim() },
      {
        onSuccess: () => {
          setNotice(`Order for ${tableName(rejecting.table_id)} rejected. The guest sees your note.`);
          setRejecting(null);
        },
        onError: (err) =>
          setError(err instanceof ApiError ? err.detail : "Could not reject the order."),
      }
    );
  }

  return (
    <Screen
      refreshing={pending.isRefetching || calls.isRefetching}
      onRefresh={() => {
        void pending.refetch();
        void calls.refetch();
      }}
    >
      <View style={{ gap: space[5] }}>
        <View style={{ gap: space[1] }}>
          <Title>Requests</Title>
          <Subtitle>
            QR orders wait here until a staff member confirms them. Guests only reach the kitchen
            after you accept.
          </Subtitle>
        </View>

        {notice ? <Banner tone="success">{notice}</Banner> : null}
        {error ? <Banner tone="danger">{error}</Banner> : null}

        <View style={{ gap: space[3] }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: space[2] }}>
            <SectionLabel>Awaiting confirmation</SectionLabel>
            <CountPill value={pendingOrders.length} tone="warn" />
          </View>

          {pending.isPending ? <Loading label="Loading QR orders" /> : null}
          {!pending.isPending && pendingOrders.length === 0 ? (
            <EmptyState icon="checkmark-done-outline" title="Nothing waiting">
              New QR orders appear here the moment a guest submits one.
            </EmptyState>
          ) : null}

          {pendingOrders.map((order) => {
            const busy = accept.isPending || reject.isPending;
            return (
              <Card key={order.id}>
                <View
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    gap: space[3],
                  }}
                >
                  <View style={{ gap: 2, flex: 1 }}>
                    <Text style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}>
                      {tableName(order.table_id)}
                    </Text>
                    <Muted>
                      Guest order · {elapsed(order.submitted_at, now)} ago · v{order.version}
                    </Muted>
                  </View>
                  <Badge status={order.status} />
                </View>

                <View style={{ gap: space[2] }}>
                  {order.items.map((item) => (
                    <View
                      key={item.id}
                      style={{ flexDirection: "row", gap: space[2], alignItems: "flex-start" }}
                    >
                      <Text
                        style={{
                          fontSize: text.base,
                          fontWeight: "700",
                          color: c.primary,
                          minWidth: 26,
                        }}
                      >
                        {item.quantity}×
                      </Text>
                      <View style={{ flex: 1 }}>
                        <Text style={{ fontSize: text.base, color: c.ink }}>
                          {item.item_name_snapshot}
                        </Text>
                        {item.special_instructions ? (
                          <Text style={{ fontSize: text.xs, color: c.warn }}>
                            Note: {item.special_instructions}
                          </Text>
                        ) : null}
                      </View>
                      <Text style={{ fontSize: text.sm, color: c.muted }}>
                        {formatMoney(item.line_total_minor, item.currency_code)}
                      </Text>
                    </View>
                  ))}
                </View>

                {order.customer_note ? (
                  <View
                    style={{
                      backgroundColor: c.surface2,
                      borderRadius: radius.md,
                      padding: space[3],
                    }}
                  >
                    <Text style={{ fontSize: text.xs, fontWeight: "700", color: c.muted }}>
                      Guest note
                    </Text>
                    <Text style={{ fontSize: text.sm, color: c.ink }}>{order.customer_note}</Text>
                  </View>
                ) : null}

                <View
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                    borderTopWidth: 1,
                    borderTopColor: c.line,
                    paddingTop: space[3],
                  }}
                >
                  <Text style={{ fontSize: text.sm, color: c.muted }}>Total</Text>
                  <Text style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}>
                    {formatMoney(order.total_minor, "USD")}
                  </Text>
                </View>

                <View style={{ flexDirection: "row", gap: space[2] }}>
                  <View style={{ flex: 1 }}>
                    <Button
                      label="Accept"
                      icon="checkmark"
                      loading={accept.isPending && accept.variables === order.id}
                      disabled={busy}
                      onPress={() => confirmAccept(order)}
                      accessibilityHint="Sends this order to the kitchen"
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Button
                      label="Reject"
                      variant="secondary"
                      icon="close"
                      disabled={busy}
                      onPress={() => openReject(order)}
                      accessibilityHint="Rejects the order and tells the guest why"
                    />
                  </View>
                </View>
              </Card>
            );
          })}
        </View>

        <View style={{ gap: space[3] }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: space[2] }}>
            <SectionLabel>Service calls</SectionLabel>
            <CountPill value={openCalls.length} tone="info" />
          </View>

          {calls.isPending ? <Loading label="Loading service calls" /> : null}
          {!calls.isPending && openCalls.length === 0 ? (
            <EmptyState icon="notifications-off-outline" title="No open calls">
              Guest requests and “food ready” signals from the kitchen appear here.
            </EmptyState>
          ) : null}

          {openCalls.map((call) => (
            <ServiceCallCard
              key={call.id}
              call={call}
              now={now}
              busy={acknowledge.isPending && acknowledge.variables === call.id}
              onAcknowledge={() => {
                setError(null);
                acknowledge.mutate(call.id, {
                  onSuccess: () => setNotice(`${call.table_display_name} acknowledged.`),
                  onError: (err) =>
                    setError(
                      err instanceof ApiError ? err.detail : "Could not acknowledge the call."
                    ),
                });
              }}
            />
          ))}
        </View>
      </View>

      <Sheet
        visible={Boolean(rejecting)}
        onClose={() => setRejecting(null)}
        title={rejecting ? `Reject order for ${tableName(rejecting.table_id)}` : "Reject order"}
        subtitle="The guest sees your note on their status page. Be specific and polite."
        footer={
          <>
            <Button
              label={reject.isPending ? "Rejecting…" : "Reject order"}
              variant="danger"
              loading={reject.isPending}
              onPress={submitReject}
            />
            <Button label="Keep it open" variant="ghost" onPress={() => setRejecting(null)} />
          </>
        }
      >
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space[2] }}>
          {REJECT_REASONS.map((reason) => {
            const selected = reasonCode === reason.code;
            return (
              <Text
                key={reason.code}
                accessibilityRole="button"
                accessibilityState={{ selected }}
                onPress={() => {
                  setReasonCode(reason.code);
                  setNote(reason.note);
                }}
                style={{
                  paddingHorizontal: space[3],
                  paddingVertical: space[2],
                  borderRadius: radius.pill,
                  borderWidth: 1,
                  borderColor: selected ? c.primary : c.lineStrong,
                  backgroundColor: selected ? c.primarySoft : c.surface,
                  color: selected ? c.primary : c.ink,
                  fontSize: text.sm,
                  fontWeight: "600",
                  overflow: "hidden",
                }}
              >
                {reason.label}
              </Text>
            );
          })}
        </View>

        <Field
          label="Note for the guest"
          value={note}
          onChangeText={setNote}
          placeholder="Tell the guest what happened and what to do next."
          multiline
          numberOfLines={3}
          maxLength={280}
          style={{ minHeight: 84, textAlignVertical: "top" }}
          hint={`${note.length}/280`}
        />

        {error ? <Banner tone="danger">{error}</Banner> : null}
      </Sheet>
    </Screen>
  );
}

function CountPill({ value, tone }: { value: number; tone: "warn" | "info" }) {
  const theme = useTheme();
  const c = theme.color;
  const fg = tone === "warn" ? c.warn : c.info;
  const bg = tone === "warn" ? c.warnSoft : c.infoSoft;
  return (
    <View
      style={{
        borderRadius: radius.pill,
        backgroundColor: bg,
        paddingHorizontal: space[2],
        paddingVertical: 2,
        marginBottom: space[2],
      }}
    >
      <Text style={{ fontSize: text.xs, fontWeight: "800", color: fg }}>{value}</Text>
    </View>
  );
}

function ServiceCallCard({
  call,
  now,
  busy,
  onAcknowledge,
}: {
  call: ServiceCall;
  now: number;
  busy: boolean;
  onAcknowledge: () => void;
}) {
  const theme = useTheme();
  const c = theme.color;
  const isKitchen = call.kind === "KITCHEN";

  return (
    <Card>
      <View style={{ flexDirection: "row", gap: space[3], alignItems: "flex-start" }}>
        <View
          style={{
            width: 36,
            height: 36,
            borderRadius: radius.pill,
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: isKitchen ? c.successSoft : c.infoSoft,
          }}
        >
          <Ionicons
            name={isKitchen ? "restaurant" : "hand-left"}
            size={18}
            color={isKitchen ? c.success : c.info}
          />
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={{ fontSize: text.base, fontWeight: "800", color: c.ink }}>
            {call.table_display_name}
          </Text>
          <Text style={{ fontSize: text.sm, color: c.muted }}>
            {isKitchen
              ? `Kitchen says ticket ${call.ticket_number ?? "—"} is ready for pickup`
              : "Guest is asking for service"}
            {" · "}
            {elapsed(call.requested_at, now)} ago
          </Text>
          {call.items_summary ? (
            <Text style={{ fontSize: text.sm, color: c.ink }}>{call.items_summary}</Text>
          ) : null}
          <Text style={{ fontSize: text.xs, color: c.muted }}>
            Status: {formatStatus(call.status)}
          </Text>
        </View>
      </View>
      <Button
        label={busy ? "Acknowledging…" : "Acknowledge"}
        variant="secondary"
        icon="checkmark-done"
        loading={busy}
        onPress={onAcknowledge}
      />
    </Card>
  );
}
