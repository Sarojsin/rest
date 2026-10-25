import { Ionicons } from "@expo/vector-icons";
import { forwardRef } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextInputProps,
  type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useTheme } from "../theme/context";
import { radius, space, tap, text } from "../theme/tokens";
import { statusColors, formatStatus, type Tone, toneColors } from "./status";

export type IconName = React.ComponentProps<typeof Ionicons>["name"];

/* -------------------------------------------------------------------------
   Layout
   ------------------------------------------------------------------------- */

export function Screen({
  children,
  scroll = true,
  padded = true,
  footer,
  edges = ["top", "left", "right"],
  refreshing,
  onRefresh,
}: {
  children: React.ReactNode;
  scroll?: boolean;
  padded?: boolean;
  footer?: React.ReactNode;
  edges?: ("top" | "right" | "bottom" | "left")[];
  refreshing?: boolean;
  onRefresh?: () => void;
}) {
  const theme = useTheme();
  const body = (
    <View style={[styles.flex, padded && { padding: space[4] }]}>{children}</View>
  );
  return (
    <SafeAreaView
      edges={edges}
      style={[styles.flex, { backgroundColor: theme.color.bg }]}
    >
      {scroll ? (
        <ScrollView
          style={styles.flex}
          contentContainerStyle={{ flexGrow: 1 }}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            onRefresh ? (
              <RefreshControl
                refreshing={Boolean(refreshing)}
                onRefresh={onRefresh}
                tintColor={theme.color.primary}
                colors={[theme.color.primary]}
              />
            ) : undefined
          }
        >
          {body}
        </ScrollView>
      ) : (
        body
      )}
      {footer}
    </SafeAreaView>
  );
}

export function Card({
  children,
  style,
  onPress,
  accessibilityLabel,
}: {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
  accessibilityLabel?: string;
}) {
  const theme = useTheme();
  const base: StyleProp<ViewStyle> = [
    styles.card,
    { backgroundColor: theme.color.surface, borderColor: theme.color.line },
    style,
  ];
  if (!onPress) return <View style={base}>{children}</View>;
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      style={({ pressed }) => [base, pressed && { opacity: 0.85 }]}
    >
      {children}
    </Pressable>
  );
}

export function Divider({ style }: { style?: StyleProp<ViewStyle> }) {
  const theme = useTheme();
  return <View style={[{ height: 1, backgroundColor: theme.color.line }, style]} />;
}

/* -------------------------------------------------------------------------
   Text
   ------------------------------------------------------------------------- */

export function Title({ children }: { children: React.ReactNode }) {
  const theme = useTheme();
  return (
    <Text
      accessibilityRole="header"
      style={{ fontSize: text.xl, fontWeight: "700", color: theme.color.ink }}
    >
      {children}
    </Text>
  );
}

export function Subtitle({ children }: { children: React.ReactNode }) {
  const theme = useTheme();
  return (
    <Text style={{ fontSize: text.base, color: theme.color.muted, lineHeight: 21 }}>
      {children}
    </Text>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  const theme = useTheme();
  return (
    <Text
      style={{
        fontSize: text.xs,
        fontWeight: "700",
        letterSpacing: 0.8,
        textTransform: "uppercase",
        color: theme.color.muted,
        marginBottom: space[2],
      }}
    >
      {children}
    </Text>
  );
}

export function Muted({ children }: { children: React.ReactNode }) {
  const theme = useTheme();
  return (
    <Text style={{ fontSize: text.sm, color: theme.color.muted }}>{children}</Text>
  );
}

/* -------------------------------------------------------------------------
   Button
   ------------------------------------------------------------------------- */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success";

export function Button({
  label,
  onPress,
  variant = "primary",
  icon,
  disabled,
  loading,
  busyLabel,
  fullWidth = true,
  accessibilityHint,
}: {
  label: string;
  onPress: () => void;
  variant?: ButtonVariant;
  icon?: IconName;
  disabled?: boolean;
  loading?: boolean;
  busyLabel?: string;
  fullWidth?: boolean;
  accessibilityHint?: string;
}) {
  const theme = useTheme();
  const c = theme.color;
  const palette: Record<ButtonVariant, { bg: string; fg: string; border: string }> = {
    primary: { bg: c.primary, fg: c.onPrimary, border: c.primary },
    secondary: { bg: c.surface, fg: c.ink, border: c.lineStrong },
    ghost: { bg: "transparent", fg: c.primary, border: "transparent" },
    danger: { bg: c.danger, fg: "#ffffff", border: c.danger },
    success: { bg: c.success, fg: "#ffffff", border: c.success },
  };
  const p = palette[variant];
  const inert = disabled || loading;

  return (
    <Pressable
      onPress={onPress}
      disabled={inert}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: Boolean(inert), busy: Boolean(loading) }}
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor: p.bg,
          borderColor: p.border,
          opacity: inert ? 0.5 : pressed ? 0.85 : 1,
          alignSelf: fullWidth ? "stretch" : "flex-start",
        },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={p.fg} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={18} color={p.fg} /> : null}
          <Text style={[styles.buttonLabel, { color: p.fg }]}>
            {loading ? (busyLabel ?? label) : label}
          </Text>
        </>
      )}
    </Pressable>
  );
}

/* -------------------------------------------------------------------------
   Badge / Banner
   ------------------------------------------------------------------------- */

export function Badge({ status, label }: { status: string; label?: string }) {
  const theme = useTheme();
  const { fg, bg } = statusColors(theme, status);
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <Text style={{ fontSize: text.xs, fontWeight: "700", color: fg }}>
        {label ?? formatStatus(status)}
      </Text>
    </View>
  );
}

export function ToneBadge({ tone, label }: { tone: Tone; label: string }) {
  const theme = useTheme();
  const { fg, bg } = toneColors(theme, tone);
  return (
    <View style={[styles.badge, { backgroundColor: bg }]}>
      <Text style={{ fontSize: text.xs, fontWeight: "700", color: fg }}>{label}</Text>
    </View>
  );
}

export type BannerTone = "info" | "success" | "warn" | "danger";

export function Banner({
  tone = "info",
  title,
  children,
  action,
}: {
  tone?: BannerTone;
  title?: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  const theme = useTheme();
  const c = theme.color;
  const map: Record<BannerTone, { fg: string; bg: string; icon: IconName }> = {
    info: { fg: c.info, bg: c.infoSoft, icon: "information-circle" },
    success: { fg: c.success, bg: c.successSoft, icon: "checkmark-circle" },
    warn: { fg: c.warn, bg: c.warnSoft, icon: "alert-circle" },
    danger: { fg: c.danger, bg: c.dangerSoft, icon: "close-circle" },
  };
  const t = map[tone];
  return (
    <View
      accessibilityRole="alert"
      style={[styles.banner, { backgroundColor: t.bg, borderColor: t.fg }]}
    >
      <Ionicons name={t.icon} size={18} color={t.fg} style={{ marginTop: 1 }} />
      <View style={styles.flex}>
        {title ? (
          <Text style={{ fontSize: text.base, fontWeight: "700", color: t.fg }}>
            {title}
          </Text>
        ) : null}
        {children ? (
          <Text style={{ fontSize: text.sm, color: theme.color.ink, lineHeight: 20 }}>
            {children}
          </Text>
        ) : null}
        {action}
      </View>
    </View>
  );
}

/* -------------------------------------------------------------------------
   States
   ------------------------------------------------------------------------- */

export function EmptyState({
  icon = "file-tray-outline",
  title,
  children,
  action,
}: {
  icon?: IconName;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  const theme = useTheme();
  return (
    <View style={styles.empty}>
      <View
        style={[
          styles.emptyIcon,
          { backgroundColor: theme.color.surface2, borderColor: theme.color.line },
        ]}
      >
        <Ionicons name={icon} size={26} color={theme.color.muted} />
      </View>
      <Text
        style={{
          fontSize: text.md,
          fontWeight: "700",
          color: theme.color.ink,
          textAlign: "center",
        }}
      >
        {title}
      </Text>
      {children ? (
        <Text
          style={{
            fontSize: text.sm,
            color: theme.color.muted,
            textAlign: "center",
            lineHeight: 20,
            maxWidth: 320,
          }}
        >
          {children}
        </Text>
      ) : null}
      {action}
    </View>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  const theme = useTheme();
  return (
    <View style={styles.loading} accessibilityRole="progressbar" accessibilityLabel={label}>
      <ActivityIndicator color={theme.color.primary} />
      <Text style={{ fontSize: text.sm, color: theme.color.muted }}>{label}</Text>
    </View>
  );
}

/* -------------------------------------------------------------------------
   Inputs
   ------------------------------------------------------------------------- */

export const Field = forwardRef<
  React.ComponentRef<typeof TextInput>,
  TextInputProps & { label: string; hint?: string }
>(function Field({ label, hint, style, ...props }, ref) {
    const theme = useTheme();
    return (
      <View style={{ gap: space[2] }}>
        <Text style={{ fontSize: text.sm, fontWeight: "600", color: theme.color.ink }}>
          {label}
        </Text>
        <TextInput
          ref={ref}
          accessibilityLabel={label}
          placeholderTextColor={theme.color.muted}
          style={[
            styles.input,
            {
              backgroundColor: theme.color.surface,
              borderColor: theme.color.lineStrong,
              color: theme.color.ink,
            },
            style,
          ]}
          {...props}
        />
        {hint ? (
          <Text style={{ fontSize: text.xs, color: theme.color.muted }}>{hint}</Text>
        ) : null}
      </View>
    );
  }
);

export function Stepper({
  value,
  onChange,
  min = 0,
  max = 99,
  label,
}: {
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  label: string;
}) {
  const theme = useTheme();
  const c = theme.color;
  const step = (delta: number) => {
    const next = Math.min(max, Math.max(min, value + delta));
    if (next !== value) onChange(next);
  };
  return (
    <View style={styles.stepper} accessibilityLabel={label}>
      <Pressable
        onPress={() => step(-1)}
        disabled={value <= min}
        accessibilityRole="button"
        accessibilityLabel={`Remove one ${label}`}
        style={({ pressed }) => [
          styles.stepButton,
          {
            borderColor: c.lineStrong,
            backgroundColor: c.surface,
            opacity: value <= min ? 0.4 : pressed ? 0.7 : 1,
          },
        ]}
      >
        <Ionicons name="remove" size={20} color={c.ink} />
      </Pressable>
      <Text
        accessibilityLabel={`${value} ${label}`}
        style={{
          minWidth: 32,
          textAlign: "center",
          fontSize: text.md,
          fontWeight: "700",
          color: c.ink,
        }}
      >
        {value}
      </Text>
      <Pressable
        onPress={() => step(1)}
        disabled={value >= max}
        accessibilityRole="button"
        accessibilityLabel={`Add one ${label}`}
        style={({ pressed }) => [
          styles.stepButton,
          {
            borderColor: c.lineStrong,
            backgroundColor: c.surface,
            opacity: value >= max ? 0.4 : pressed ? 0.7 : 1,
          },
        ]}
      >
        <Ionicons name="add" size={20} color={c.ink} />
      </Pressable>
    </View>
  );
}

/* -------------------------------------------------------------------------
   Key/value rows
   ------------------------------------------------------------------------- */

export function KeyValue({
  label,
  value,
  emphasis,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
}) {
  const theme = useTheme();
  return (
    <View style={styles.keyValue}>
      <Text style={{ fontSize: emphasis ? text.md : text.sm, color: theme.color.muted }}>
        {label}
      </Text>
      <Text
        style={{
          fontSize: emphasis ? text.md : text.sm,
          fontWeight: emphasis ? "700" : "600",
          color: theme.color.ink,
        }}
      >
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  card: {
    borderRadius: radius.lg,
    borderWidth: 1,
    padding: space[4],
    gap: space[3],
  },
  button: {
    minHeight: tap,
    borderRadius: radius.md,
    borderWidth: 1,
    paddingHorizontal: space[4],
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: space[2],
  },
  buttonLabel: { fontSize: text.md, fontWeight: "700" },
  badge: {
    borderRadius: radius.pill,
    paddingHorizontal: space[3],
    paddingVertical: 4,
    alignSelf: "flex-start",
  },
  banner: {
    borderRadius: radius.md,
    borderWidth: 1,
    padding: space[3],
    flexDirection: "row",
    gap: space[3],
    alignItems: "flex-start",
  },
  empty: {
    alignItems: "center",
    justifyContent: "center",
    gap: space[3],
    paddingVertical: space[8],
    paddingHorizontal: space[4],
  },
  emptyIcon: {
    width: 56,
    height: 56,
    borderRadius: radius.pill,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  loading: {
    flexDirection: "row",
    alignItems: "center",
    gap: space[3],
    paddingVertical: space[6],
    justifyContent: "center",
  },
  input: {
    minHeight: tap,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: space[3],
    paddingVertical: space[2],
    fontSize: text.md,
  },
  stepper: { flexDirection: "row", alignItems: "center", gap: space[3] },
  stepButton: {
    width: 40,
    height: 40,
    borderRadius: radius.pill,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  keyValue: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    gap: space[3],
  },
});
