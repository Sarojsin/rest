import { Ionicons } from "@expo/vector-icons";
import { useKeepAwake } from "expo-keep-awake";
import * as Haptics from "expo-haptics";
import { useMemo, useState } from "react";
import { Pressable, Text, useWindowDimensions, View } from "react-native";

import type { KitchenTicket, KitchenTicketItem } from "@rest/api-client";

import {
  Badge,
  Banner,
  Button,
  Card,
  EmptyState,
  Loading,
  Muted,
  Screen,
  Subtitle,
  Title,
} from "@/components/ui";
import { useCallWaiter, useSetItemStatus, useTickets } from "@/features/kitchen/api";
import { useTableNames } from "@/features/tables/api";
import { ApiError } from "@/lib/api";
import { elapsed, isLate } from "@/lib/format";
import { useNow } from "@/lib/useNow";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

type ColumnKey = "NEW" | "IN_PROGRESS" | "READY";

const COLUMNS: { key: ColumnKey; title: string; hint: string; empty: string }[] = [
  {
    key: "NEW",
    title: "New",
    hint: "Accepted, not started",
    empty: "No new tickets. Accepted guest orders land here.",
  },
  {
    key: "IN_PROGRESS",
    title: "Cooking",
    hint: "On the line right now",
    empty: "Nothing on the line.",
  },
  {
    key: "READY",
    title: "Ready",
    hint: "Waiting for pickup",
    empty: "Nothing waiting for pickup.",
  },
];

export default function KitchenBoardScreen() {
  // A kitchen tablet is mounted on a wall; letting the screen sleep mid-service
  // is worse than the battery cost.
  useKeepAwake();

  const theme = useTheme();
  const c = theme.color;
  const { width } = useWindowDimensions();
  const wide = width >= 900;
  const now = useNow();
  const tableName = useTableNames();

  const tickets = useTickets();
  const setStatus = useSetItemStatus();
  const callWaiter = useCallWaiter();

  const [activeColumn, setActiveColumn] = useState<ColumnKey>("NEW");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const grouped = useMemo(() => {
    const map: Record<ColumnKey, KitchenTicket[]> = {
      NEW: [],
      IN_PROGRESS: [],
      READY: [],
    };
    for (const ticket of tickets.data ?? []) {
      const bucket: ColumnKey =
        ticket.status === "READY" ? "READY" : ticket.status === "NEW" ? "NEW" : "IN_PROGRESS";
      map[bucket].push(ticket);
    }
    return map;
  }, [tickets.data]);

  const openCount = grouped.NEW.length + grouped.IN_PROGRESS.length;

  function moveItem(item: KitchenTicketItem, status: "PREPARING" | "READY" | "SERVED") {
    setError(null);
    setNotice(null);
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setStatus.mutate(
      { itemId: item.id, status },
      {
        onError: (err) =>
          setError(
            err instanceof ApiError
              ? `Could not update ${item.item_name ?? "item"}: ${err.detail}`
              : "Could not update the item."
          ),
      }
    );
  }

  function signal(ticket: KitchenTicket) {
    setError(null);
    setNotice(null);
    void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    callWaiter.mutate(ticket.id, {
      onSuccess: () => setNotice(`Ticket ${ticket.ticket_number} marked ready and the floor called.`),
      onError: (err) =>
        setError(err instanceof ApiError ? err.detail : "Could not signal the service team."),
    });
  }

  const columnsToRender = wide ? COLUMNS : COLUMNS.filter((column) => column.key === activeColumn);

  return (
    <Screen
      refreshing={tickets.isRefetching}
      onRefresh={() => void tickets.refetch()}
    >
      <View style={{ gap: space[4] }}>
        <View style={{ gap: space[1] }}>
          <Title>Kitchen board</Title>
          <Subtitle>
            {openCount === 0
              ? "No open tickets."
              : `${openCount} open ticket${openCount === 1 ? "" : "s"} on the line.`}{" "}
            Tickets only appear after staff accept a QR order.
          </Subtitle>
        </View>

        {error ? <Banner tone="danger">{error}</Banner> : null}
        {notice ? <Banner tone="success">{notice}</Banner> : null}

        {!wide ? (
          <View
            style={{
              flexDirection: "row",
              backgroundColor: c.surface2,
              borderRadius: radius.md,
              padding: 4,
              gap: 4,
            }}
          >
            {COLUMNS.map((column) => {
              const selected = column.key === activeColumn;
              return (
                <Pressable
                  key={column.key}
                  onPress={() => setActiveColumn(column.key)}
                  accessibilityRole="tab"
                  accessibilityState={{ selected }}
                  accessibilityLabel={`${column.title}, ${grouped[column.key].length} tickets`}
                  style={{
                    flex: 1,
                    minHeight: 40,
                    borderRadius: radius.sm,
                    alignItems: "center",
                    justifyContent: "center",
                    flexDirection: "row",
                    gap: 6,
                    backgroundColor: selected ? c.surface : "transparent",
                  }}
                >
                  <Text
                    style={{
                      fontSize: text.sm,
                      fontWeight: "700",
                      color: selected ? c.ink : c.muted,
                    }}
                  >
                    {column.title}
                  </Text>
                  <View
                    style={{
                      minWidth: 20,
                      paddingHorizontal: 5,
                      borderRadius: radius.pill,
                      backgroundColor: selected ? c.primarySoft : c.surface3,
                      alignItems: "center",
                    }}
                  >
                    <Text
                      style={{
                        fontSize: text.xs,
                        fontWeight: "800",
                        color: selected ? c.primary : c.muted,
                      }}
                    >
                      {grouped[column.key].length}
                    </Text>
                  </View>
                </Pressable>
              );
            })}
          </View>
        ) : null}

        {tickets.isPending ? <Loading label="Loading tickets" /> : null}

        <View style={{ flexDirection: wide ? "row" : "column", gap: space[3] }}>
          {columnsToRender.map((column) => {
            const columnTickets = grouped[column.key];
            return (
              <View key={column.key} style={{ flex: wide ? 1 : undefined, gap: space[3] }}>
                <View
                  style={{
                    flexDirection: "row",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: space[3],
                  }}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}>
                      {column.title}
                    </Text>
                    <Text style={{ fontSize: text.xs, color: c.muted }}>{column.hint}</Text>
                  </View>
                  <View
                    style={{
                      minWidth: 28,
                      paddingHorizontal: space[2],
                      paddingVertical: 2,
                      borderRadius: radius.pill,
                      backgroundColor: c.surface3,
                      alignItems: "center",
                    }}
                  >
                    <Text style={{ fontSize: text.xs, fontWeight: "800", color: c.ink }}>
                      {columnTickets.length}
                    </Text>
                  </View>
                </View>

                {columnTickets.length === 0 ? (
                  <View
                    style={{
                      borderWidth: 1,
                      borderStyle: "dashed",
                      borderColor: c.lineStrong,
                      borderRadius: radius.lg,
                      padding: space[4],
                    }}
                  >
                    <Text style={{ fontSize: text.sm, color: c.muted, textAlign: "center" }}>
                      {column.empty}
                    </Text>
                  </View>
                ) : null}

                {columnTickets.map((ticket) => (
                  <TicketCard
                    key={ticket.id}
                    ticket={ticket}
                    column={column.key}
                    now={now}
                    tableName={tableName}
                    busyItemId={setStatus.isPending ? (setStatus.variables?.itemId ?? null) : null}
                    calling={callWaiter.isPending && callWaiter.variables === ticket.id}
                    onMove={moveItem}
                    onSignal={() => signal(ticket)}
                  />
                ))}
              </View>
            );
          })}
        </View>

        {!tickets.isPending && (tickets.data?.length ?? 0) === 0 ? (
          <EmptyState icon="restaurant-outline" title="The board is clear">
            Accepted orders appear here within a few seconds.
          </EmptyState>
        ) : null}

        <Text style={{ fontSize: text.xs, color: c.muted }}>
          Item states move new → cooking → ready → served. The floor is only alerted when you press
          “All ready — call waiter”.
        </Text>
      </View>
    </Screen>
  );
}

function TicketCard({
  ticket,
  column,
  now,
  tableName,
  busyItemId,
  calling,
  onMove,
  onSignal,
}: {
  ticket: KitchenTicket;
  column: ColumnKey;
  now: number;
  tableName: (id: string) => string;
  busyItemId: string | null;
  calling: boolean;
  onMove: (item: KitchenTicketItem, status: "PREPARING" | "READY" | "SERVED") => void;
  onSignal: () => void;
}) {
  const theme = useTheme();
  const c = theme.color;

  const activeItems = ticket.items.filter((item) => item.status !== "CANCELLED");
  const openItems = activeItems.filter((item) => item.status !== "READY" && item.status !== "SERVED");
  const itemCount = activeItems.reduce((total, item) => total + item.quantity_snapshot, 0);

  // Once nothing is cooking the created-at clock stops being meaningful: show
  // how long the food has been waiting instead of claiming the kitchen is slow.
  const doneCooking =
    activeItems.length > 0 &&
    activeItems.every((item) => item.status === "READY" || item.status === "SERVED");
  const allServed = activeItems.length > 0 && activeItems.every((item) => item.status === "SERVED");
  const timeRef = doneCooking ? (ticket.ready_at ?? ticket.created_at) : ticket.created_at;
  const late = !doneCooking && isLate(ticket.created_at, now);

  const accent =
    column === "NEW" ? c.info : column === "READY" ? c.success : c.warn;

  return (
    <Card style={{ borderLeftWidth: 4, borderLeftColor: accent }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", gap: space[3] }}>
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}>
            Ticket {ticket.ticket_number}
          </Text>
          <Muted>
            {ticket.table_display_name ?? tableName(ticket.order_id)} · {itemCount} item
            {itemCount === 1 ? "" : "s"}
          </Muted>
        </View>
        <View style={{ alignItems: "flex-end", gap: 2 }}>
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: 4,
              paddingHorizontal: space[2],
              paddingVertical: 2,
              borderRadius: radius.pill,
              backgroundColor: late ? c.dangerSoft : c.surface2,
            }}
          >
            <Ionicons
              name="time-outline"
              size={12}
              color={late ? c.danger : c.muted}
            />
            <Text
              style={{
                fontSize: text.xs,
                fontWeight: "800",
                color: late ? c.danger : c.muted,
              }}
            >
              {elapsed(timeRef, now)}
            </Text>
          </View>
          <Text style={{ fontSize: text.xs, color: c.muted }}>
            {allServed ? "delivered" : doneCooking ? "waiting for pickup" : late ? "running long" : ""}
          </Text>
        </View>
      </View>

      <View style={{ gap: space[2] }}>
        {ticket.items.map((item) => {
          const ready = item.status === "READY";
          return (
            <View
              key={item.id}
              style={{
                flexDirection: "row",
                alignItems: "center",
                gap: space[3],
                paddingVertical: space[2],
                borderTopWidth: 1,
                borderTopColor: c.line,
              }}
            >
              <View style={{ flex: 1, gap: 2 }}>
                <Text style={{ fontSize: text.base, color: c.ink }}>
                  <Text style={{ fontWeight: "800", color: c.primary }}>
                    {item.quantity_snapshot}×{" "}
                  </Text>
                  {item.item_name ?? "Item"}
                </Text>
                {item.instructions_snapshot ? (
                  <Text style={{ fontSize: text.xs, color: c.warn }}>
                    Note: {item.instructions_snapshot}
                  </Text>
                ) : null}
                <Text style={{ fontSize: text.xs, color: ready ? c.success : c.muted }}>
                  {item.status === "CANCELLED"
                    ? "Cancelled"
                    : item.status === "SERVED"
                      ? "Served"
                      : item.status === "READY"
                        ? "Ready"
                        : item.status === "PREPARING"
                          ? "Cooking"
                          : "Not started"}
                </Text>
              </View>

              {item.status !== "CANCELLED" && item.status !== "SERVED" ? (
                <View style={{ minWidth: 92 }}>
                  {item.status === "NEW" ? (
                    <Button
                      label="Start"
                      fullWidth
                      loading={busyItemId === item.id}
                      onPress={() => onMove(item, "PREPARING")}
                    />
                  ) : null}
                  {item.status === "PREPARING" ? (
                    <Button
                      label="Ready"
                      variant="success"
                      fullWidth
                      loading={busyItemId === item.id}
                      onPress={() => onMove(item, "READY")}
                    />
                  ) : null}
                  {item.status === "READY" ? (
                    <Button
                      label="Served"
                      variant="secondary"
                      fullWidth
                      loading={busyItemId === item.id}
                      onPress={() => onMove(item, "SERVED")}
                    />
                  ) : null}
                </View>
              ) : (
                <Badge status={item.status} />
              )}
            </View>
          );
        })}
      </View>

      {column === "READY" ? (
        <Button
          label="Call service again"
          variant="secondary"
          loading={calling}
          onPress={onSignal}
        />
      ) : (
        <Button
          label={calling ? "Signalling…" : "All ready — call waiter"}
          variant="success"
          icon="notifications"
          loading={calling}
          disabled={openItems.length === 0}
          onPress={onSignal}
        />
      )}
    </Card>
  );
}
