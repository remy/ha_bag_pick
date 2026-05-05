![Disclosure: made with AI](https://badgen.net/badge/disclosure/made%20with%20ai)

# Bag Pick

A Home Assistant custom integration that picks random items from a preset list using the **bag pick** (shuffle bag) method — items are drawn without replacement until the bag is exhausted, at which point the bag automatically refills and reshuffles. No item repeats until every item has been seen.

![Bag Pick icon](icon.png)

---

## Installation

1. Copy the `bag_pick` folder into your `custom_components` directory:
   ```
   config/
   └── custom_components/
       └── bag_pick/
   ```
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Bag Pick**.

---

## Setup

Each bag is configured through the UI — no YAML required.

### Creating a bag

1. **Settings → Devices & Services → Add Integration → Bag Pick**
2. Fill in a **bag name** (e.g. `Morning Playlist`)
3. Either:
   - Enter **items** directly, one per line, or
   - Enter a **generator** expression (see [Generator Templates](#generator-templates) below) — takes precedence over the items list if both are filled
4. Submit. The sensor is immediately initialised with a first pick.

### Editing a bag

Click **Configure** on the integration card. The options flow has two steps:

1. **Edit** — update the items list or generator expression
2. **Preview** — see the full resolved list before committing. Tick **Save these items** and submit to save, or leave unticked and submit to go back and edit.

> **Note:** Editing items resets the current bag cycle.

> **Tip:** The items textarea requires **Shift+Enter** to add new lines (this is a Home Assistant frontend limitation). It's easier to paste pre-prepared content.

---

## Entities

Each bag creates two sensor entities on a single device:

### `sensor.<bag_name>`

The **current picked item**.

| Attribute | Description                      |
| --------- | -------------------------------- |
| `total`   | Total number of items in the bag |
| `items`   | Full master items list           |

### `sensor.<bag_name>_remaining`

The **number of items remaining** in the current cycle.

| Attribute | Description                                  |
| --------- | -------------------------------------------- |
| `items`   | The remaining items in current shuffle order |

---

## Services

Both services target sensor entities.

### `bag_pick.pick_next`

Picks the next item from the bag. If the bag is exhausted after the pick, it automatically refills and reshuffles — so the bag is always primed for the next call.

```yaml
service: bag_pick.pick_next
target:
  entity_id: sensor.morning_playlist
```

### `bag_pick.reset`

Forces a reshuffle from the full master list immediately, discarding the current cycle.

```yaml
service: bag_pick.reset
target:
  entity_id: sensor.morning_playlist
```

---

## Generator Templates

The generator field accepts any **Home Assistant template expression** that evaluates to a list. The template has access to all standard HA template functions and filters.

### Numbers

```jinja
{# 1 to 52 #}
{{ range(1, 53) | list }}

{# 0 to 99 #}
{{ range(0, 100) | list }}

{# Even numbers 2–20 #}
{{ range(2, 21, 2) | list }}

{# As zero-padded strings #}
{{ range(1, 53) | map('string') | map('int') | list }}
```

### Days and dates

```jinja
{# Days of the week #}
{{ ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'] }}

{# Weekdays only #}
{{ ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] }}

{# Months #}
{{ ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'] }}
```

### Playing cards

```jinja
{# Full 52-card deck #}
{% set suits = ['♠', '♥', '♦', '♣'] %}
{% set ranks = ['A','2','3','4','5','6','7','8','9','10','J','Q','K'] %}
{% set deck = [] %}
{% for suit in suits %}
  {% for rank in ranks %}
    {% set deck = deck + [rank ~ suit] %}
  {% endfor %}
{% endfor %}
{{ deck }}
```

### Using HA state

```jinja
{# Items from an input_select entity #}
{{ state_attr('input_select.meal_options', 'options') }}

{# Names of all lights in a room #}
{{ states.light
   | selectattr('attributes.area_id', 'eq', 'living_room')
   | map(attribute='name')
   | list }}
```

### Combining lists

```jinja
{# Merge two fixed lists #}
{{ ['Alpha', 'Bravo', 'Charlie'] + ['Delta', 'Echo', 'Foxtrot'] }}

{# Repeat each item N times #}
{% set items = ['Red', 'Blue', 'Green'] %}
{% set repeated = [] %}
{% for item in items %}
  {% for _ in range(3) %}
    {% set repeated = repeated + [item] %}
  {% endfor %}
{% endfor %}
{{ repeated }}
```

---

## Example Automations

### Pick from a bag on button press

```yaml
automation:
  - alias: "Pick next workout"
    trigger:
      - platform: state
        entity_id: input_button.next_workout
    action:
      - service: bag_pick.pick_next
        target:
          entity_id: sensor.workout_rotation
```

### Daily pick at a set time

```yaml
automation:
  - alias: "Daily meal pick"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: bag_pick.pick_next
        target:
          entity_id: sensor.meal_plan
```

### Announce the current pick via TTS

```yaml
automation:
  - alias: "Announce current pick"
    trigger:
      - platform: state
        entity_id: sensor.morning_playlist
    action:
      - service: tts.speak
        data:
          message: "Now playing {{ states('sensor.morning_playlist') }}"
```

### Reset all bags at the start of the month

```yaml
automation:
  - alias: "Monthly bag reset"
    trigger:
      - platform: time
        at: "00:00:00"
    condition:
      - condition: template
        value_template: "{{ now().day == 1 }}"
    action:
      - service: bag_pick.reset
        target:
          entity_id:
            - sensor.morning_playlist
            - sensor.workout_rotation
            - sensor.meal_plan
```

---

## How the bag pick works

1. On first use, the master items list is shuffled into the bag
2. Each `pick_next` call pops the next item from the shuffled bag
3. When the bag becomes empty after a pick, it is **immediately refilled and reshuffled** — so the bag is always ready for the next call
4. The bag state (current item + remaining items) is persisted to `.storage/bag_pick.<entry_id>` and survives restarts
5. The master items list is persisted in the config entry and survives restarts independently of the bag state
