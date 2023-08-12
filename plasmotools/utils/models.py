import logging

import databases
import orm

from plasmotools import settings

database = databases.Database("sqlite:///" + settings.DATABASE_PATH)
models = orm.ModelRegistry(database)

logger = logging.getLogger(__name__)


class RRSRole(orm.Model):
    tablename = "rrs_roles"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "structure_guild_id": orm.BigInteger(),
        "structure_role_id": orm.BigInteger(),
        "plasmo_role_id": orm.BigInteger(),
        "verified_by_plasmo": orm.Boolean(default=False),
        "disabled": orm.Boolean(default=False),
    }


class RRSAction(orm.Model):
    tablename = "rrs_actions"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "structure_role_id": orm.BigInteger(),
        "target_id": orm.BigInteger(),
        "author_id": orm.BigInteger(),
        "approved_by_user_id": orm.BigInteger(),
        "is_role_granted": orm.Boolean(),
        "reason": orm.String(max_length=256, allow_blank=True),
        "date": orm.DateTime(),
    }


class StructureGuild(orm.Model):
    tablename = "structure_guilds"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "discord_id": orm.BigInteger(unique=True),
        "alias": orm.String(max_length=32),
        "player_role_id": orm.BigInteger(),
        "head_role_id": orm.BigInteger(),
        "public_chat_channel_id": orm.BigInteger(),
        "logs_channel_id": orm.BigInteger(),
    }


class StructurePayout(orm.Model):
    tablename = "structure_payouts_history"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "project_id": orm.Integer(),
        "user_id": orm.BigInteger(),
        "payer_id": orm.BigInteger(),
        "is_paid": orm.Boolean(),
        "from_card_str": orm.String(max_length=2 + 1 + 4),
        "to_card_str": orm.String(max_length=2 + 1 + 4),
        "amount": orm.Integer(),
        "message": orm.String(max_length=256, allow_blank=True),
        "date": orm.DateTime(),
    }


class StructureProject(orm.Model):
    tablename = "structure_projects"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "name": orm.String(
            max_length=32,
        ),
        "is_active": orm.Boolean(default=False),
        "guild_discord_id": orm.Integer(),
        "from_card_str": orm.String(max_length=2 + 1 + 4),
        "plasmo_bearer_token": orm.String(
            max_length=256,
        ),
        "webhook_url": orm.String(
            max_length=256,
        ),
    }


class StructureRole(orm.Model):
    tablename = "structure_roles"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "name": orm.String(
            max_length=32,
        ),
        "guild_discord_id": orm.Integer(),
        "role_discord_id": orm.Integer(unique=True),
        "is_available": orm.Boolean(default=True),
        "webhook_url": orm.String(
            max_length=256,
        ),
    }


class PersonalSettings(orm.Model):
    tablename = "personal_settings"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "discord_id": orm.BigInteger(unique=True),
        "saved_card_str": orm.String(max_length=2 + 1 + 4),
        "bearer_token": orm.String(max_length=256, allow_null=True),
        "rp_token": orm.String(max_length=256, allow_null=True),
        "blocked": orm.Boolean(default=False),
        "allow_pings_in_payouts": orm.Boolean(default=True),
        "announce_events_in_mc_dms": orm.Boolean(default=True),
        "send_roles_logs_in_dms": orm.Boolean(default=False),
    }


class Patent(orm.Model):
    tablename = "patents"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "subject": orm.String(max_length=256),
        "is_art": orm.Boolean(),
        "map_ids": orm.String(max_length=1024, allow_null=True),
        "owner_ids": orm.String(max_length=1024),
        "registration_date": orm.DateTime(),
        "banker_id": orm.BigInteger(),
        "status": orm.String(
            max_length=16, default="WAIT"
        ),  # WAIT, APPROVED, REJECTED, AUTOAPPROVED
        "moderator_id": orm.BigInteger(allow_null=True),
        "message_id": orm.BigInteger(allow_null=True),
        "total_price": orm.Integer(),
        "price_breakdown": orm.String(max_length=256),  # Example: 15;5;10
        "is_payment_on_hold": orm.Boolean(default=True),
        "from_card_str": orm.String(max_length=2 + 1 + 4),
        "is_refunded": orm.Boolean(default=False),
        "is_lamination_skipped": orm.Boolean(default=False),
    }


async def setup_database():
    logger.info("Creating tables")
    await models.create_all()
