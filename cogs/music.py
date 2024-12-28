import discord
import wavelink
import datetime

from typing import cast, Optional
from wavelink import TrackSource
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

EMBEDTITLE = "Music"

class Music(commands.Cog, name="music"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print("Connecting to Lavalink node...")
        nodes = [wavelink.Node(uri="http://127.0.0.1:2333", password="youshallnotpass")]
        await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=None)
        

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload) -> None:
        print(f"Wavelink Node connected: {payload.node!r} | Resumed: {payload.resumed}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        
        if not player:
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track

        embed = discord.Embed(title=f":notes: {track.title}", color=discord.Color.blurple())
        embed.add_field(name="Playtime", value=str(datetime.timedelta(milliseconds=int(track.length))), inline=True)
        embed.add_field(name="Link", value=f"[Click Here]({track.uri})", inline=True)
        

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        if original and original.recommended:
            embed.description = f"\n\n(Added by autoplay)"

        await player.home.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            return
        
        members = set()
        for member in player.channel.members:
            members.add(member.id)

        if len(members) <= 1:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description="There are no more users in the voice channel, so playback has been stopped.",
                color=discord.Color.blurple()
            )

            await player.home.send(embed=embed)
            await player.stop(force=True)
            player.autoplay = wavelink.AutoPlayMode.disabled
            return
        
        if player.autoplay == wavelink.AutoPlayMode.enabled:
            return
        else:
            try:
                await player.play(player.queue.get(), volume=30)
            except:
                pass

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.player) -> None:
        embed = discord.Embed(
            title=EMBEDTITLE,
            description=f"Disconnected from the voice channel due to inactivity for `{player.inactive_timeout}` seconds.",
            color=discord.Color.blurple()
        )
        await player.home.send(embed=embed)
        player.autoplay = wavelink.AutoPlayMode.disabled
        await player.disconnect()


    @commands.hybrid_command(
        name="join",
        description="Connect to voice channel"
    )
    async def join(self, context: Context, channel: Optional[discord.VoiceChannel]):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        if channel is None:
            channel = context.author.voice.channel

        if not player:
            try:
                player = await channel.connect(cls=wavelink.Player)  # type: ignore
                embed = discord.Embed(
                    title=EMBEDTITLE,
                    description=f"Connected to `{channel.name}`.",
                    color=discord.Color.blurple()
                )
                await context.send(embed=embed)
            except Exception as e:
                embed = discord.Embed(
                    title=EMBEDTITLE,
                    description=f"Unable to connect to the voice channel.",
                    color=discord.Color.red()
                )
                return await context.send(embed=embed)


    @commands.hybrid_command(
        name="leave",
        description="Leave from the connected voice channel"
    )
    async def leave(self, context: Context):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        if not player:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"There is no connected voice channel.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)

        embed = discord.Embed(
            title=EMBEDTITLE,
            description=f"Disconnected from the voice channel.",
            color=discord.Color.blurple()
        )
        await player.disconnect()
        await context.send(embed=embed)


    @commands.hybrid_command(
        name="p",
        description="Play a track"
    )
    @app_commands.describe(query="Query or URL")
    async def play(self, context: Context, *, query: str):
        player: wavelink.Player
        player = cast(wavelink.Player, context.voice_client)

        if not player:
            try:
                player = await context.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
            except AttributeError:
                embed = discord.Embed(
                    title=EMBEDTITLE,
                    description=f"There is no connected voice channel.",
                    color=discord.Color.red()
                )       
                return await context.send(embed=embed)
            except discord.ClientException:
                embed = discord.Embed(
                    title=EMBEDTITLE,
                    description=f"Unable to join the voice channel.",
                    color=discord.Color.red()
                )
                return await context.send(embed=embed)
                
            
        if not hasattr(player, "home"):
            player.home = context.channel
        elif player.home != context.channel:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Songs can only be played in {player.home.mention}.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)
        
        tracks: wavelink.Search = await wavelink.Playable.search(query, source=TrackSource.YouTube)
        if not tracks:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Unable to find the song.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)
            
        player.autoplay = wavelink.AutoPlayMode.disabled
        player.inactive_timeout = 60

        if isinstance(tracks, wavelink.Playlist):
            added: int = await player.queue.put_wait(tracks)
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Playlist **`{tracks.name}`** ({added} tracks) has been added to the queue.",
                color=discord.Color.blurple()
            )
            await context.send(embed=embed)
        else:
            track: wavelink.Playable = tracks[0]
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"**`{track}`** has been added to the queue.",
                color=discord.Color.blurple()
            )
            await player.queue.put_wait(track)
            await context.send(embed=embed)

        if not player.playing:
            await player.play(player.queue.get(), volume=30)



    @commands.hybrid_command(
        name="pause",
        description="Pause/Resume current track",
    )
    async def pause(self, context: Context):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        if not player:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"There is no song currently playing.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)

        if not player.paused:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Pausing the song.",
                color=discord.Color.blurple()
            )
            await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Resuming the song.",
                color=discord.Color.blurple()
            )
            await context.send(embed=embed)
        await player.pause(not player.paused)


    @commands.hybrid_command(
        name="skip",
        description="Skip current track"
    )
    async def skip(self, context: Context):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        if not player:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"There is no song currently playing.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)

        embed = discord.Embed(
            title=EMBEDTITLE,
            description=f"Skipping `{player.current.title}`.",
            color=discord.Color.blurple()
        )
        await context.send(embed=embed)
        await player.skip(force=True)

        
    @commands.hybrid_command(
        name="nowplaying",
        description="Display current track",
        aliases=["np"]
        )
    async def nowplaying(self, context: Context):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        if not player:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"There is no song currently playing.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)

        if player.playing:
            track = player.current

            embed = discord.Embed(title=f":notes: {track.title}", color=discord.Color.blurple())
            embed.add_field(name="Playtime", value=str(datetime.timedelta(milliseconds=int(track.length))), inline=True)
            embed.add_field(name="Link", value=f"[Click Here]({track.uri})", inline=True)

            return await context.send(embed=embed)

    

    @commands.hybrid_command(
        name="queue",
        description="Display current queue"
    )
    async def queue(self, context: Context):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        
        if not player:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"There is no song currently playing.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)
        else:
            queue = player.queue
        
        if queue.is_empty == False:
            playtime = 0
            for i, track in enumerate(queue):
                playtime += track.length
            
            playtime = datetime.timedelta(milliseconds=playtime)

            embed = discord.Embed(
                title=f":notes: Playlist ({playtime}): ",
                description="\n".join(f"**{i+1}. {track}**" for i, track in enumerate(queue)),
                color=discord.Color.blurple()
            )
            return await context.send(embed=embed)
        
        else:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Queue is empty.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)


    @commands.hybrid_command(
        name='remove',
        description='Remove a track from the queue'
    )
    @app_commands.describe(number="Track number")
    async def remove(self, context: Context, number: int):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        queue = player.queue

        if number <= 0:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Please enter an integer greater than or equal to 1.",
                color=discord.Color.red()
            )
            return await context.reply(embed=embed)
        else:
            try:
                removed_track = queue[number-1]
                queue.delete(number-1)
                embed = discord.Embed(
                    title=EMBEDTITLE,
                    description=f"Removed `{removed_track.title}`을(를) 재생목록에서 제거하였습니다.",
                    color=discord.Color.blurple()
                )
                return await context.send(embed=embed)
            except:
                embed = discord.Embed(
                    title=EMBEDTITLE,
                    description=f"An error occurred while removing the track.",
                    color=discord.Color.red()
                )
                return await context.send(embed=embed)


    @commands.hybrid_command(
        name="autoplay",
        description="Set autoplay mode"
    )
    async def autoplay(self, context: Context):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)

        if not player:
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"There is no song currently playing.",
                color=discord.Color.red()
            )
            return await context.send(embed=embed)

        if player.autoplay == wavelink.AutoPlayMode.enabled:
            player.autoplay = wavelink.AutoPlayMode.disabled
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Autoplay has been disabled.",
                color=discord.Color.blurple()
            )
            return await context.send(embed=embed)
        else:
            player.autoplay = wavelink.AutoPlayMode.enabled
            embed = discord.Embed(
                title=EMBEDTITLE,
                description=f"Autoplay has been enabled.\nThis feature will be disabled when a new song is added.",
                color=discord.Color.blurple()
            )
            return await context.send(embed=embed)

    

    @commands.hybrid_command(
        name='loop',
        description='[WIP] Set repeat mode'
    )
    async def loop(self, context: Context):
        embed = discord.Embed(
            title=EMBEDTITLE,
            description=f"This feature is currently under development.",
            color=discord.Color.yellow()
        )
        return await context.send(embed=embed)
    

    @commands.hybrid_command(
        name="shuffle",
        description="Shuffle the queue"
    )
    async def shuffle(self, context: Context):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        queue = player.queue
        queue.shuffle()

        embed = discord.Embed(
            title=EMBEDTITLE,
            description=f"The queue has been shuffled",
            color=discord.Color.blurple()
        )
        await context.send(embed=embed)
    
    
    @commands.hybrid_command(
        name="swap",
        description="Swap two tracks"
    )
    @app_commands.describe(first="The song number to change", second="The song number to change")
    async def swap(self, context: Context, first: int, second: int):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        queue = player.queue
        queue.swap(first-1, second-1)

        embed = discord.Embed(
            title=EMBEDTITLE,
            description=f"Swapped\n`{queue[first-1]}`\nand\n`{queue[second-1]}`.",
            color=discord.Color.blurple()
        )
        await context.send(embed=embed)


    @commands.hybrid_command(
        name="empty",
        description="Clear the queue"
    )
    async def empty(self, context: Context):
        player: wavelink.Player = cast(wavelink.Player, context.voice_client)
        queue = player.queue
        queue.reset()

        embed = discord.Embed(
            title=EMBEDTITLE,
            description=f"The queue has been cleared.",
            color=discord.Color.blurple()
        )
        await context.send(embed=embed)
    


async def setup(bot):
    await bot.add_cog(Music(bot))
