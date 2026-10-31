import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useMemo } from "react";
import { useWindowDimensions, View, Text } from "react-native";

import type { Table } from "@rest/api-client";

import { Badge, Banner, Button, Card, EmptyState, Loading, Screen, Subtitle, Title } from "@/components/ui";
import { useTables } from "@/features/tables/api";
import { useTheme } from "@/theme/context";
import { radius, space, text } from "@/theme/tokens";

/**
 * Floor overview. The table list is the waiter's home: occupancy, open
 * sessions, and how many QR orders are still waiting for confirmation.
 */
export default function WaiterTablesScreen() {
  const theme = useTheme();
  const c = theme.color;
  const { width } = useWindowDimensions();
  const tables = useTables();

  const columns = width >= 1000 ? 4 : width >= 700 ? 3 : 2;
  const rows = tables.data ?? [];

  const summary = useMemo(() => {
    let free = 0;
    let occupied = 0;
    let pending = 0;
    for (const table of rows) {
      if (table.occupancy === "OCCUPIED" || table.active_session_id) occupied += 1;
      else free += 1;
      pending += table.pending_qr_count;
    }
    return { free, occupied, pending };
  }, [rows]);

  const gap = space[3];
  const cardWidth = (width - space[4] * 2 - gap * (columns - 1)) / columns;

  return (
    <Screen
      refreshing={tables.isRefetching}
      onRefresh={() => void tables.refetch()}
    >
      <View style={{ gap: space[4] }}>
        <View style={{ gap: space[1] }}>
          <Title>Tables</Title>
          <Subtitle>Tap a table to see its session and take an order.</Subtitle>
        </View>

        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: space[2] }}>
          <SummaryChip icon="ellipse-outline" label={`${summary.free} free`} />
          <SummaryChip icon="people" label={`${summary.occupied} occupied`} />
          {summary.pending > 0 ? (
            <SummaryChip
              icon="time-outline"
              label={`${summary.pending} awaiting confirmation`}
              tone="warn"
            />
          ) : null}
        </View>

        {tables.isError ? (
          <Banner tone="danger" title="Could not load tables">
            {tables.error instanceof Error ? tables.error.message : "Check the connection."}
          </Banner>
        ) : null}

        {tables.isPending ? <Loading label="Loading tables" /> : null}

        {!tables.isPending && rows.length === 0 && !tables.isError ? (
          <EmptyState icon="grid-outline" title="No tables yet">
            An owner or manager adds tables in the staff website. They appear here as soon as they
            are created.
          </EmptyState>
        ) : null}

        <View style={{ flexDirection: "row", flexWrap: "wrap", gap }}>
          {rows.map((table) => (
            <TableCard
              key={table.id}
              table={table}
              width={cardWidth}
              onPress={() => router.push(`/waiter/order/${table.id}`)}
            />
          ))}
        </View>

        {rows.length > 0 ? (
          <Button
            label="Awaiting confirmation"
            icon="notifications-outline"
            variant={summary.pending > 0 ? "primary" : "secondary"}
            onPress={() => router.push("/waiter/requests")}
          />
        ) : null}
      </View>
    </Screen>
  );
}

function SummaryChip({
  icon,
  label,
  tone = "neutral",
}: {
  icon: React.ComponentProps<typeof Ionicons>["name"];
  label: string;
  tone?: "neutral" | "warn";
}) {
  const theme = useTheme();
  const c = theme.color;
  const fg = tone === "warn" ? c.warn : c.muted;
  const bg = tone === "warn" ? c.warnSoft : c.surface2;
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: 6,
        paddingHorizontal: space[3],
        paddingVertical: 6,
        borderRadius: radius.pill,
        backgroundColor: bg,
      }}
    >
      <Ionicons name={icon} size={14} color={fg} />
      <Text style={{ fontSize: text.xs, fontWeight: "700", color: fg }}>{label}</Text>
    </View>
  );
}

function TableCard({
  table,
  width,
  onPress,
}: {
  table: Table;
  width: number;
  onPress: () => void;
}) {
  const theme = useTheme();
  const c = theme.color;
  const occupied = table.occupancy === "OCCUPIED" || Boolean(table.active_session_id);

  return (
    <Card
      onPress={onPress}
      accessibilityLabel={`Table ${table.display_name}${
        occupied ? ", occupied" : ", free"
      }${table.pending_qr_count > 0 ? `, ${table.pending_qr_count} awaiting confirmation` : ""}`}
      style={{ width, minHeight: 118, justifyContent: "space-between" }}
    >
      <View style={{ gap: 2 }}>
        <Text
          numberOfLines={1}
          style={{ fontSize: text.md, fontWeight: "800", color: c.ink }}
        >
          {table.display_name}
        </Text>
        <Text style={{ fontSize: text.xs, color: c.muted }}>
          {table.seating_capacity ? `${table.seating_capacity} seats` : "No seat count"}
        </Text>
      </View>

      <View style={{ gap: space[2] }}>
        <Badge status={occupied ? "OCCUPIED" : "AVAILABLE"} />
        {table.pending_qr_count > 0 ? (
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: 4,
              backgroundColor: c.warnSoft,
              borderRadius: radius.pill,
              paddingHorizontal: space[2],
              paddingVertical: 3,
              alignSelf: "flex-start",
            }}
          >
            <Ionicons name="time-outline" size={12} color={c.warn} />
            <Text style={{ fontSize: text.xs, fontWeight: "700", color: c.warn }}>
              {table.pending_qr_count} pending
            </Text>
          </View>
        ) : null}
      </View>
    </Card>
  );
}
