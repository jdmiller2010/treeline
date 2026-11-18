import type * as React from 'react';

export type IconName =
  | 'phone' | 'phone-incoming' | 'phone-outgoing' | 'phone-off' | 'bell' | 'moon' | 'sun' | 'pause'
  | 'check' | 'close' | 'plus' | 'clock' | 'leaf' | 'users' | 'lock' | 'chevron-right'
  | 'shield-check' | 'ladder' | 'home';

export type Status = 'available' | 'ringing' | 'on-call' | 'quiet' | 'paused' | 'offline';

export interface IconProps { name: IconName; size?: 16 | 20 | 24 | number; label?: string; className?: string }
export declare function Icon(props: IconProps): React.ReactElement;

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'quiet' | 'danger' | 'ring';
  size?: 'sm' | 'md' | 'lg';
  icon?: IconName;
  iconEnd?: IconName;
  fullWidth?: boolean;
  /** In compact top bars, show the icon only (label stays for screen readers). */
  collapse?: boolean;
}
export declare function Button(props: ButtonProps): React.ReactElement;

export interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: IconName;
  /** Required: the accessible name and tooltip. */
  label: string;
  variant?: 'quiet' | 'secondary' | 'primary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
}
export declare function IconButton(props: IconButtonProps): React.ReactElement;

export interface TagProps { tone?: 'neutral' | 'canopy' | 'bark' | 'sky' | 'sunbeam' | 'berry'; icon?: IconName; children?: React.ReactNode; className?: string }
export declare function Tag(props: TagProps): React.ReactElement;

export interface PresenceProps { status: Status; label?: string; showIcon?: boolean; className?: string }
export declare function Presence(props: PresenceProps): React.ReactElement;

export interface AvatarProps { name: string; size?: 'sm' | 'md' | 'lg'; status?: Status; tone?: 'moss' | 'acorn' | 'pond' | 'petal' | 'sun'; className?: string }
export declare function Avatar(props: AvatarProps): React.ReactElement;

export interface SwitchProps { label?: string; description?: string; checked?: boolean; defaultChecked?: boolean; onChange?: (next: boolean) => void; disabled?: boolean; id?: string; className?: string }
export declare function Switch(props: SwitchProps): React.ReactElement;

export interface CheckboxProps { label?: string; description?: string; checked?: boolean; defaultChecked?: boolean; onChange?: (next: boolean) => void; disabled?: boolean; id?: string; className?: string }
export declare function Checkbox(props: CheckboxProps): React.ReactElement;

export interface TextFieldProps extends React.InputHTMLAttributes<HTMLInputElement> { label?: string; hint?: string; error?: string; icon?: IconName }
export declare function TextField(props: TextFieldProps): React.ReactElement;

export interface CardProps { title?: React.ReactNode; eyebrow?: string; action?: React.ReactNode; tone?: 'sun' | 'plank' | 'dusk' | 'night'; elevated?: boolean; as?: string; children?: React.ReactNode; className?: string }
export declare function Card(props: CardProps): React.ReactElement;

export interface FriendRowProps { name: string; household?: string; speedDial?: string; status?: Status; action?: React.ReactNode; onClick?: () => void; className?: string }
export declare function FriendRow(props: FriendRowProps): React.ReactElement;

export interface ApprovalCardProps { kid: string; friend: string; yourHousehold?: string; theirHousehold?: string; yours: boolean; theirs: boolean; actions?: React.ReactNode; className?: string }
export declare function ApprovalCard(props: ApprovalCardProps): React.ReactElement;

export interface QuietHoursProps { title?: string; start: string; end: string; days?: string[]; activeDays?: number[]; on?: boolean; onToggle?: (next: boolean) => void; id?: string; className?: string }
export declare function QuietHours(props: QuietHoursProps): React.ReactElement;

export interface CallLogItemProps { kind: 'incoming' | 'outgoing' | 'missed' | 'blocked' | 'time-limit'; from: string; to: string; time: string; duration?: string; reason?: string; className?: string }
export declare function CallLogItem(props: CallLogItemProps): React.ReactElement;

export type IllustrationName = 'treehouse' | 'connection' | 'quiet' | 'sprig';
export interface IllustrationProps { name: IllustrationName; width?: number; label?: string; className?: string }
export declare function Illustration(props: IllustrationProps): React.ReactElement;

export interface EmptyStateProps { illustration?: IllustrationName; title?: React.ReactNode; action?: React.ReactNode; children?: React.ReactNode; className?: string }
export declare function EmptyState(props: EmptyStateProps): React.ReactElement;

export interface AlertProps { tone?: "info" | "success" | "warning" | "danger"; title?: React.ReactNode; children?: React.ReactNode; actions?: React.ReactNode; icon?: string; onClose?: () => void; /** Show the dismiss button in plain HTML (js/treeline.js removes the alert). */ dismissible?: boolean; className?: string }
export declare function Alert(props: AlertProps): React.ReactElement;
export interface ToastProps { tone?: "neutral" | "success" | "warning"; children: React.ReactNode; action?: React.ReactNode; onAction?: () => void; icon?: string; className?: string }
export declare function Toast(props: ToastProps): React.ReactElement;
/** The fixed region toasts stack in. Put it in AppShell's overlay. */
export declare function Toasts(props: { children?: React.ReactNode }): React.ReactElement;
export interface SelectOption { value: string; label: string; disabled?: boolean }
export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> { label?: string; hint?: string; error?: string; options: Array<SelectOption | string>; id?: string }
export declare function Select(props: SelectProps): React.ReactElement;
export interface TimeFieldProps extends React.InputHTMLAttributes<HTMLInputElement> { label?: string; hint?: string; error?: string; id?: string }
export declare function TimeField(props: TimeFieldProps): React.ReactElement;
export interface TimeRangeProps { label?: string; startLabel?: string; endLabel?: string; start?: string; end?: string; defaultStart?: string; defaultEnd?: string; onStartChange?: (e: any) => void; onEndChange?: (e: any) => void; hint?: string; id?: string; className?: string }
export declare function TimeRange(props: TimeRangeProps): React.ReactElement;
export interface SegmentOption { value: string; label: string; icon?: string; disabled?: boolean }
export interface SegmentedControlProps { label: string; options: Array<SegmentOption | string>; value?: string; defaultValue?: string; onChange?: (value: string) => void; fullWidth?: boolean; name?: string; className?: string }
export declare function SegmentedControl(props: SegmentedControlProps): React.ReactElement;
export interface MenuItem { label?: string; icon?: string; href?: string; onSelect?: (e: any) => void; danger?: boolean; separator?: boolean }
export interface MenuProps { items: MenuItem[]; trigger?: React.ReactElement; label?: string; header?: { name: string; meta?: string }; align?: "end" | "start"; defaultOpen?: boolean; id?: string; className?: string }
export declare function Menu(props: MenuProps): React.ReactElement;
export interface RadioOption { value: string; label: string; description?: string; disabled?: boolean }
export interface RadioGroupProps { label: string; options: RadioOption[]; value?: string; defaultValue?: string; onChange?: (v: string) => void; variant?: "plain" | "cards"; name?: string; className?: string }
export declare function RadioGroup(props: RadioGroupProps): React.ReactElement;
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> { label?: string; hint?: string; error?: string; id?: string }
export declare function Textarea(props: TextareaProps): React.ReactElement;
export interface PasswordFieldProps extends React.InputHTMLAttributes<HTMLInputElement> { label?: string; hint?: string; error?: string; id?: string }
export declare function PasswordField(props: PasswordFieldProps): React.ReactElement;
export interface CodeInputProps { label?: string; length?: number; split?: boolean; defaultValue?: string; hint?: string; error?: string; id?: string; className?: string }
export declare function CodeInput(props: CodeInputProps): React.ReactElement;
export interface SliderProps { label: string; min?: number; max?: number; step?: number; value?: number; defaultValue?: number; onChange?: (v: number) => void; unit?: string; format?: (v: number) => string; minLabel?: string; maxLabel?: string; id?: string; className?: string }
export declare function Slider(props: SliderProps): React.ReactElement;
export interface BadgeProps { count?: number | string; dot?: boolean; tone?: "alert" | "quiet"; label?: string; children?: React.ReactNode; className?: string }
export declare function Badge(props: BadgeProps): React.ReactElement;
export interface StepsProps { steps: string[]; current: number; label?: string; className?: string }
export declare function Steps(props: StepsProps): React.ReactElement;
export interface ProgressBarProps { label?: string; value?: number; className?: string }
export declare function ProgressBar(props: ProgressBarProps): React.ReactElement;
export interface DescriptionListProps { items: Array<{ label: string; value: React.ReactNode }>; className?: string }
export declare function DescriptionList(props: DescriptionListProps): React.ReactElement;
export interface SkeletonProps { variant?: "text" | "title" | "circle" | "row"; width?: string | number; size?: number; className?: string }
export declare function Skeleton(props: SkeletonProps): React.ReactElement;
export interface DisclosureProps { title: React.ReactNode; children?: React.ReactNode; defaultOpen?: boolean; className?: string }
export declare function Disclosure(props: DisclosureProps): React.ReactElement;
export declare function Accordion(props: { children?: React.ReactNode; className?: string }): React.ReactElement;
export interface StatTileProps { label: string; value: React.ReactNode; unit?: string; note?: React.ReactNode; trend?: boolean; className?: string }
export declare function StatTile(props: StatTileProps): React.ReactElement;
export interface TabsProps { label: string; tabs: Array<{ value: string; label: string; content: React.ReactNode; badge?: number }>; value?: string; defaultValue?: string; onChange?: (v: string) => void; id?: string; className?: string }
export declare function Tabs(props: TabsProps): React.ReactElement;
export interface RotaryPhoneApi { lift(): void; hangUp(): void; dial(digit: number): void; isOffHook(): boolean }
export interface RotaryPhoneProps {
  /** The treehouse's own 4-digit number, shown in the middle of the dial. */ number?: string;
  colorway?: "moss" | "ivory" | "berry";
  /** Controlled hook state. Leave out to let taps on the handset lift and hang up. */ offHook?: boolean;
  defaultOffHook?: boolean;
  /** Called with each dialed digit while the handset is lifted, once the dial has returned. */ onDigit?: (digit: number) => void;
  onHook?: (offHook: boolean) => void;
  /** Once per pulse while the dial returns: play a click here. */ onPulse?: (e: { digit: number; pulse: number }) => void;
  /** The "Can't call 911" line under the phone. On by default; only turn it off where the screen already says it. */ notice?: boolean;
  apiRef?: { current: RotaryPhoneApi | null }; id?: string; className?: string;
}
export declare function RotaryPhone(props: RotaryPhoneProps): React.ReactElement;
export interface NavItem { icon: string; label: string; href?: string; current?: boolean; /** A count badge on the icon, e.g. waiting approvals. */ badge?: number; badgeLabel?: string; onClick?: (e: any) => void }
export interface NavBarProps { items: NavItem[]; brand?: React.ReactNode; footer?: React.ReactNode; label?: string; className?: string }
export declare function NavBar(props: NavBarProps): React.ReactElement;
export declare function Brand(props: { href?: string; className?: string }): React.ReactElement;
export interface AppBarProps { title: React.ReactNode; lead?: React.ReactNode; actions?: React.ReactNode; className?: string }
export declare function AppBar(props: AppBarProps): React.ReactElement;
export interface AppShellProps { bar?: React.ReactNode; nav?: React.ReactNode; /** Sheets and dialogs. Rendered outside main so they cover the whole app. */ overlay?: React.ReactNode; children?: React.ReactNode; className?: string; style?: React.CSSProperties }
export declare function AppShell(props: AppShellProps): React.ReactElement;
export interface SheetProps { title: React.ReactNode; children?: React.ReactNode; actions?: React.ReactNode; open?: boolean; /** Plain HTML: render closed with the hidden attribute and open it with data-tl-open. */ hidden?: boolean; onClose?: () => void; id?: string; className?: string }
export declare function Sheet(props: SheetProps): React.ReactElement | null;
export interface LeafDividerProps { className?: string }
export declare function LeafDivider(props: LeafDividerProps): React.ReactElement;

export interface LeafLoaderProps { size?: number; label?: string | false; showLabel?: boolean; className?: string }
export declare function LeafLoader(props: LeafLoaderProps): React.ReactElement;

declare global {
  interface Window {
    Treeline: {
      Icon: typeof Icon; Button: typeof Button; IconButton: typeof IconButton; Tag: typeof Tag; Presence: typeof Presence; Avatar: typeof Avatar;
      Switch: typeof Switch; Checkbox: typeof Checkbox; TextField: typeof TextField; Card: typeof Card;
      FriendRow: typeof FriendRow; ApprovalCard: typeof ApprovalCard; QuietHours: typeof QuietHours; CallLogItem: typeof CallLogItem;
      Illustration: typeof Illustration; EmptyState: typeof EmptyState; LeafDivider: typeof LeafDivider; LeafLoader: typeof LeafLoader;
      Alert: typeof Alert; Toast: typeof Toast; Toasts: typeof Toasts; Select: typeof Select; TimeField: typeof TimeField; TimeRange: typeof TimeRange; SegmentedControl: typeof SegmentedControl; Menu: typeof Menu; RadioGroup: typeof RadioGroup; Textarea: typeof Textarea; PasswordField: typeof PasswordField; CodeInput: typeof CodeInput; Slider: typeof Slider; Badge: typeof Badge; Steps: typeof Steps; ProgressBar: typeof ProgressBar; DescriptionList: typeof DescriptionList; Skeleton: typeof Skeleton; Disclosure: typeof Disclosure; Accordion: typeof Accordion; StatTile: typeof StatTile; Tabs: typeof Tabs; RotaryPhone: typeof RotaryPhone;
      Brand: typeof Brand; NavBar: typeof NavBar; AppBar: typeof AppBar; AppShell: typeof AppShell; Sheet: typeof Sheet;
      iconNames: IconName[]; illustrationNames: IllustrationName[];
    };
  }
}
