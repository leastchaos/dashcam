#!C:\Python Projects\dashcam\venv\Scripts\python.exe
import datetime
import sys
from importlib import metadata
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Optional

from gopro_overlay import timeseries_process, gpmd_filters
from gopro_overlay.arguments import gopro_dashboard_arguments
from gopro_overlay.assertion import assert_file_exists
from gopro_overlay.buffering import SingleBuffer, DoubleBuffer
from gopro_overlay.common import temp_file_name
from gopro_overlay.config import Config
from gopro_overlay.counter import ReasonCounter
from gopro_overlay.date_overlap import DateRange
from gopro_overlay.dimensions import dimension_from
from gopro_overlay.execution import InProcessExecution
from gopro_overlay.ffmpeg import FFMPEG
from gopro_overlay.ffmpeg_gopro import FFMPEGGoPro
from gopro_overlay.ffmpeg_overlay import FFMPEGNull, FFMPEGOverlay, FFMPEGOverlayVideo
from gopro_overlay.ffmpeg_profile import load_ffmpeg_profile
from gopro_overlay.font import load_font
from gopro_overlay.framemeta_gpx import merge_gpx_with_gopro, timeseries_to_framemeta
from gopro_overlay.geo import MapRenderer, api_key_finder, MapStyler
from gopro_overlay.gpmf import GPS_FIXED_VALUES, GPSFix
from gopro_overlay.layout import Overlay, speed_awareness_layout
from gopro_overlay.layout_xml import layout_from_xml, load_xml_layout, Converters
from gopro_overlay.loading import load_external, GoproLoader
from gopro_overlay.log import log, fatal
from gopro_overlay.point import Point
from gopro_overlay.privacy import PrivacyZone, NoPrivacyZone
from gopro_overlay.progresstrack import ProgressBarProgress
from gopro_overlay.timeunits import timeunits, Timeunit
from gopro_overlay.timing import PoorTimer, Timers
from gopro_overlay.units import units
from gopro_overlay.widgets.profile import WidgetProfiler


def accepter_from_args(include, exclude):
    if include and exclude:
        raise ValueError("Can't use both include and exclude at the same time")

    if include:
        return lambda n: n in include
    if exclude:
        return lambda n: n not in exclude

    return lambda n: True


def create_desired_layout(
    dimensions,
    layout,
    layout_xml: Path,
    include,
    exclude,
    renderer,
    timeseries,
    font,
    privacy_zone,
    profiler,
    converters: Converters,
):
    accepter = accepter_from_args(include, exclude)

    if layout_xml:
        layout = "xml"

    if layout == "default":
        resource_name = Path(f"default-{dimensions.x}x{dimensions.y}")
        try:
            return layout_from_xml(
                load_xml_layout(resource_name),
                renderer,
                timeseries,
                font,
                privacy_zone,
                include=accepter,
                decorator=profiler,
                converters=converters,
            )
        except FileNotFoundError:
            raise IOError(
                f"Unable to locate bundled layout resource: {resource_name}. "
                f"You may need to create a custom layout for this frame size"
            ) from None

    elif layout == "speed-awareness":
        return speed_awareness_layout(renderer, font=font)
    elif layout == "xml":
        return layout_from_xml(
            load_xml_layout(layout_xml),
            renderer,
            timeseries,
            font,
            privacy_zone,
            include=accepter,
            decorator=profiler,
            converters=converters,
        )
    else:
        raise ValueError(f"Unsupported layout {args.layout_creator}")


def fmtdt(dt: datetime.datetime):
    return dt.replace(microsecond=0).isoformat()


def generate_args_list(
    input: Optional[str | Path] = None,
    output: Optional[str | Path] = "output_video.mp4",
    font: Optional[str] = "arial",
    privacy: Optional[str] = None,
    generate: Optional[str] = None,
    overlay_size: Optional[str] = "1920x1080",
    bg: Optional[tuple[int, int, int, int]] = None,
    config_dir: Optional[str | Path] = None,
    cache_dir: Optional[str | Path] = None,
    profile: Optional[str] = None,
    double_buffer: bool = False,
    ffmpeg_dir: Optional[str | Path] = None,
    load: Optional[list[str]] = None,
    gpx: Optional[str | Path] = None,
    gpx_merge: Optional[str] = None,
    use_gpx_only: bool = False,
    use_fit_only: bool = True,
    fit: Optional[str | Path] = Path("C:/Python Projects/dashcam/18404524116.fit"),
    video_time_start: Optional[str] = None,
    video_time_end: Optional[str] = None,
    map_style: Optional[str] = None,
    map_api_key: Optional[str] = None,
    layout: Optional[str] = None,
    layout_xml: Optional[str | Path] = Path(
        "C:/Python Projects/dashcam/power-1920x1080.xml"
    ),
    exclude: Optional[list[str]] = None,
    include: Optional[list[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    duration: Optional[str] = None,
    units_speed: Optional[str] = "kph",
    units_altitude: Optional[str] = "metre",
    units_distance: Optional[str] = "km",
    units_temperature: Optional[str] = "degC",
    gps_dop_max: Optional[float] = 5,
    gps_speed_max: Optional[float] = None,
    gps_speed_max_units: Optional[str] = None,
    gps_bbox_lon_lat: Optional[str] = None,
    show_ffmpeg: bool = False,
    print_timings: bool = False,
    debug_metadata: bool = False,
    profiler: bool = False,
) -> list[str]:
    """
    Args:
        input (pathlib.Path, optional): Input MP4 file.
        output (pathlib.Path): Output Video File.
        font (str, optional): Selects a font.
        privacy (str, optional): Set privacy zone (lat,lon,km).
        generate (str, optional): Type of output to generate.
        overlay_size (str, optional): <XxY> e.g. 1920x1080 Force size of overlay.
        bg (tuple, optional): Background Colour - R,G,B,A - each 0-255, no spaces!
        config_dir (pathlib.Path, optional): Location of config files.
        cache_dir (pathlib.Path, optional): Location of caches.
        profile (str, optional): Use ffmpeg options profile.
        double_buffer (bool, optional): Enable double buffering mode.
        ffmpeg_dir (pathlib.Path, optional): Directory where ffmpeg/ffprobe located.
        load (list, optional): List of LoadFlag values.
        gpx (pathlib.Path, optional): Use GPX/FIT file.
        fit (pathlib.Path, optional): Use GPX/FIT file.
        gpx_merge (str, optional): GPX/FIT merge mode.
        use_gpx_only (bool, optional): Use only GPX/FIT file.
        video_time_start (str, optional): Use file dates for aligning video start.
        video_time_end (str, optional): Use file dates for aligning video end.
        map_style (str, optional): Style of map to render.
        map_api_key (str, optional): API Key for map provider.
        layout (str, optional): Choose graphics layout.
        layout_xml (pathlib.Path, optional): Use XML File for layout.
        exclude (list, optional): Exclude named components.
        include (list, optional): Include named components.
        units_speed (str, optional): Default unit for speed.
        units_altitude (str, optional): Default unit for altitude.
        units_distance (str, optional): Default unit for distance.
        units_temperature (str, optional): Default unit for temperature.
        gps_dop_max (float, optional): Max DOP.
        gps_speed_max (float, optional): Max GPS Speed.
        gps_speed_max_units (str, optional): Units for --gps-speed-max.
        gps_bbox_lon_lat (str, optional): GPS Bounding Box.
        show_ffmpeg (bool, optional): Show FFMPEG output.
        print_timings (bool, optional): Print timings.
        debug_metadata (bool, optional): Show detailed information when parsing GoPro Metadata.
        profiler (bool, optional): Do some basic profiling of the widgets.

    Returns:
        list: List of arguments.
    """

    args_list = []

    if input is not None:
        args_list.append(str(input))
    if output is not None:
        args_list.append(str(output))
    if font is not None:
        args_list.extend(["--font", str(font)])
    if privacy is not None:
        args_list.extend(["--privacy", str(privacy)])
    if generate is not None:
        args_list.extend(["--generate", str(generate)])
    if start is not None:
        args_list.extend(["--start", str(start)])
    if end is not None:
        args_list.extend(["--end", str(end)])
    if duration is not None:
        args_list.extend(["--duration", str(duration)])
    if overlay_size is not None:
        args_list.extend(["--overlay-size", str(overlay_size)])
    if bg is not None:
        args_list.extend(["--bg", ",".join(map(str, bg))])
    if config_dir is not None:
        args_list.extend(["--config-dir", str(config_dir)])
    if cache_dir is not None:
        args_list.extend(["--cache-dir", str(cache_dir)])
    if profile is not None:
        args_list.extend(["--profile", str(profile)])
    if double_buffer:
        args_list.append("--double-buffer")
    if ffmpeg_dir is not None:
        args_list.extend(["--ffmpeg-dir", str(ffmpeg_dir)])
    if load is not None:
        args_list.extend(["--load"] + [str(item) for item in load])
    if gpx is not None:
        args_list.extend(["--gpx", str(gpx)])
    if gpx_merge is not None:
        args_list.extend(["--gpx-merge", str(gpx_merge)])
    if use_gpx_only:
        args_list.append("--use-gpx-only")
    if use_fit_only:
        args_list.append("--use-fit-only")
    if fit is not None:
        args_list.extend(["--fit", str(fit)])
    if video_time_start is not None:
        args_list.extend(["--video-time-start", str(video_time_start)])
    if video_time_end is not None:
        args_list.extend(["--video-time-end", str(video_time_end)])
    if map_style is not None:
        args_list.extend(["--map-style", str(map_style)])
    if map_api_key is not None:
        args_list.extend(["--map-api-key", str(map_api_key)])
    if layout is not None:
        args_list.extend(["--layout", str(layout)])
    if layout_xml is not None:
        args_list.extend(["--layout-xml", str(layout_xml)])
    if exclude is not None:
        args_list.extend(["--exclude"] + [str(item) for item in exclude])
    if include is not None:
        args_list.extend(["--include"] + [str(item) for item in include])
    if units_speed is not None:
        args_list.extend(["--units-speed", str(units_speed)])
    if units_altitude is not None:
        args_list.extend(["--units-altitude", str(units_altitude)])
    if units_distance is not None:
        args_list.extend(["--units-distance", str(units_distance)])
    if units_temperature is not None:
        args_list.extend(["--units-temperature", str(units_temperature)])
    if gps_dop_max is not None:
        args_list.extend(["--gps-dop-max", str(gps_dop_max)])
    if gps_speed_max is not None:
        args_list.extend(["--gps-speed-max", str(gps_speed_max)])
    if gps_speed_max_units is not None:
        args_list.extend(["--gps-speed-max-units", str(gps_speed_max_units)])
    if gps_bbox_lon_lat is not None:
        args_list.extend(["--gps-bbox-lon-lat", str(gps_bbox_lon_lat)])
    if show_ffmpeg:
        args_list.append("--show-ffmpeg")
    if print_timings:
        args_list.append("--print-timings")
    if debug_metadata:
        args_list.append("--debug-metadata")
    if profiler:
        args_list.append("--profiler")

    return args_list


def generate_dashboard(
    output: Optional[str | Path] = "output_video.mp4",
    fit: Optional[str | Path] = Path("C:/Python Projects/dashcam/18404524116.fit"),
    font: Optional[str] = "arial",
    overlay_size: Optional[str] = "1920x1080",
    layout_xml: Optional[str | Path] = Path(
        "C:/Python Projects/dashcam/power-1920x1080.xml"
    ),
    privacy: Optional[str] = "1.442770, 103.808006, 2", # (lat, long, km)
    **kwargs
    

) -> None:
    """Generate the dashboard."""
    # Define the arguments as a list
    args_list = generate_args_list(
        output=output,
        fit=fit,
        font=font,
        overlay_size=overlay_size,
        layout_xml=layout_xml,
        privacy=privacy,
        **kwargs
    )
    # Call the function with the arguments
    args = gopro_dashboard_arguments(args_list)

    try:
        version = metadata.version("gopro_overlay")
    except PackageNotFoundError:
        version = "local"

    log(f"Starting gopro-dashboard version {version}")

    ffmpeg_exe = FFMPEG(location=args.ffmpeg_dir, print_cmds=args.show_ffmpeg)

    if not ffmpeg_exe.is_installed():
        log("Can't start ffmpeg - is it installed?")
        exit(1)
    if not ffmpeg_exe.libx264_is_installed():
        log(
            "ffmpeg doesn't seem to handle libx264 files - it needs to be compiled with support for this, "
            "check your installation"
        )
        exit(1)

    try:
        log(f"ffmpeg version is {ffmpeg_exe.version()}")
    except ValueError:
        log("ffmpeg version is unknown")

    log(f"Using Python version {sys.version}")
    if sys.version_info < (3, 10):
        log(
            "*** Python version below 3.10 is not supported, please use supported version of Python"
        )

    try:
        font = load_font(args.font)
    except OSError:
        fatal(
            f"Unable to load font '{args.font}' - use --font to choose a font that is installed."
        )

    ffmpeg_gopro = FFMPEGGoPro(ffmpeg_exe)

    # need in this scope for now
    inputpath: Optional[Path] = None
    generate = args.generate
    print(f"Generate: {generate}")

    config_dir = args.config_dir
    print(f"Using config directory {config_dir}")
    config_dir.mkdir(exist_ok=True)
    print(f"Using cache directory {args.cache_dir}")

    config_loader = Config(config_dir)

    cache_dir = args.cache_dir
    cache_dir.mkdir(exist_ok=True)

    timers = Timers(printing=args.print_timings)

    try:
        with timers.timer("program"):
            with timers.timer("loading timeseries"):

                if args.use_gpx_only:

                    start_date: Optional[datetime.datetime] = None
                    end_date: Optional[datetime.datetime] = None
                    duration: Optional[Timeunit] = None

                    if args.input:
                        inputpath = assert_file_exists(args.input)
                        recording = ffmpeg_gopro.find_recording(inputpath)
                        dimensions = recording.video.dimension

                        duration = recording.video.duration

                        fns = {
                            "file-created": lambda f: f.ctime,
                            "file-modified": lambda f: f.mtime,
                            "file-accessed": lambda f: f.atime,
                        }

                        if args.video_time_start:
                            start_date = fns[args.video_time_start](recording.file)
                            end_date = start_date + duration.timedelta()

                        if args.video_time_end:
                            start_date = (
                                fns[args.video_time_end](recording.file)
                                - duration.timedelta()
                            )
                            end_date = start_date + duration.timedelta()

                    else:
                        generate = "overlay"

                    external_file: Path = assert_file_exists(args.gpx)
                    fit_or_gpx_timeseries = load_external(external_file, units)

                    log(
                        f"GPX/FIT file:     {fmtdt(fit_or_gpx_timeseries.min)} -> {fmtdt(fit_or_gpx_timeseries.max)}"
                    )

                    # Give a bit of information here about what is going on
                    if start_date is not None:
                        log(
                            f"Video File Dates: {fmtdt(start_date)} -> {fmtdt(end_date)}"
                        )

                        overlap = DateRange(
                            start=start_date, end=end_date
                        ).overlap_seconds(
                            DateRange(
                                start=fit_or_gpx_timeseries.min,
                                end=fit_or_gpx_timeseries.max,
                            )
                        )

                        if overlap == 0:
                            fatal(
                                "Video file and GPX/FIT file don't overlap in time -  See "
                                "https://github.com/time4tea/gopro-dashboard-overlay/tree/main/docs/bin#create-a-movie"
                                "-from-gpx-and-video-not-created-with-gopro"
                            )

                    frame_meta = timeseries_to_framemeta(
                        fit_or_gpx_timeseries,
                        units,
                        start_date=start_date,
                        duration=duration,
                    )
                    video_duration = frame_meta.duration()
                    packets_per_second = 10
                else:
                    inputpath = assert_file_exists(args.input)

                    counter = ReasonCounter()

                    loader = GoproLoader(
                        ffmpeg_gopro=ffmpeg_gopro,
                        units=units,
                        flags=args.load,
                        gps_lock_filter=gpmd_filters.standard(
                            dop_max=args.gps_dop_max,
                            speed_max=units.Quantity(
                                args.gps_speed_max, args.gps_speed_max_units
                            ),
                            bbox=args.gps_bbox_lon_lat,
                            report=counter.because,
                        ),
                    )

                    gopro = loader.load(inputpath)

                    gpmd_filters.poor_report(counter)

                    frame_meta = gopro.framemeta

                    dimensions = gopro.recording.video.dimension
                    video_duration = gopro.recording.video.duration
                    packets_per_second = frame_meta.packets_per_second()

                    if len(frame_meta) == 0:
                        log(
                            "No GPS Information found in the Video - Was GPS Recording enabled?"
                        )
                        log(
                            "If you have a GPX File, See https://github.com/time4tea/gopro-dashboard-overlay/tree/main"
                            "/docs/bin#create-a-movie-from-gpx-and-video-not-created-with-gopro"
                        )
                        exit(1)

                    if args.gpx:
                        external_file: Path = args.gpx
                        fit_or_gpx_timeseries = load_external(external_file, units)
                        log(
                            f"GPX/FIT file:     {fmtdt(fit_or_gpx_timeseries.min)} -> {fmtdt(fit_or_gpx_timeseries.max)}"
                        )
                        overlap = DateRange(
                            start=frame_meta.date_at(frame_meta.min),
                            end=frame_meta.date_at(frame_meta.max),
                        ).overlap_seconds(
                            DateRange(
                                start=fit_or_gpx_timeseries.min,
                                end=fit_or_gpx_timeseries.max,
                            )
                        )

                        if overlap == 0:
                            fatal(
                                "Video file and GPX/FIT file don't overlap in time -  See "
                                "https://github.com/time4tea/gopro-dashboard-overlay/tree/main/docs/bin#create-a-movie"
                                "-from-gpx-and-video-not-created-with-gopro"
                            )

                        log(
                            f"GPX/FIT Timeseries has {len(fit_or_gpx_timeseries)} data points.. merging..."
                        )
                        merge_gpx_with_gopro(
                            fit_or_gpx_timeseries, frame_meta, mode=args.gpx_merge
                        )

                if args.overlay_size:
                    dimensions = dimension_from(args.overlay_size)

            if len(frame_meta) < 1:
                fatal(
                    f"Unable to load GoPro metadata from {inputpath}. Use --debug-metadata to see more information"
                )

            log(f"Generating overlay at {dimensions}")
            log(f"Timeseries has {len(frame_meta)} data points")
            log("Processing....")

            with timers.timer("processing"):
                locked_2d = lambda e: e.gpsfix in GPS_FIXED_VALUES
                locked_3d = lambda e: e.gpsfix == GPSFix.LOCK_3D.value

                frame_meta.process(
                    timeseries_process.process_ses(
                        "point", lambda i: i.point, alpha=0.45
                    ),
                    filter_fn=locked_2d,
                )
                frame_meta.process_deltas(
                    timeseries_process.calculate_speeds(),
                    skip=packets_per_second * 3,
                    filter_fn=locked_2d,
                )
                frame_meta.process(
                    timeseries_process.calculate_odo(), filter_fn=locked_2d
                )
                frame_meta.process_accel(
                    timeseries_process.calculate_accel(), skip=18 * 3
                )
                frame_meta.process_deltas(
                    timeseries_process.calculate_gradient(),
                    skip=packets_per_second * 3,
                    filter_fn=locked_3d,
                )  # hack
                frame_meta.process(
                    timeseries_process.process_kalman("speed", lambda e: e.speed)
                )
                frame_meta.process(timeseries_process.filter_locked())

            # privacy zone applies everywhere, not just at start, so might not always be suitable...
            if args.privacy:
                lat, lon, km = args.privacy.split(",")
                privacy_zone = PrivacyZone(
                    Point(float(lat), float(lon)), units.Quantity(float(km), units.km)
                )
            else:
                privacy_zone = NoPrivacyZone()

            with MapRenderer(
                cache_dir=cache_dir,
                styler=MapStyler(api_key_finder=api_key_finder(config_loader, args)),
            ).open(args.map_style) as renderer:

                if args.profiler:
                    profiler = WidgetProfiler()
                else:
                    profiler = None

                if args.profile:
                    ffmpeg_options = load_ffmpeg_profile(config_loader, args.profile)
                else:
                    ffmpeg_options = None

                if args.show_ffmpeg:
                    redirect = None
                else:
                    redirect = temp_file_name(suffix=".txt")
                    log(f"FFMPEG Output is in {redirect}")

                execution = InProcessExecution(redirect=redirect)

                output: Path = args.output

                if generate == "none":
                    ffmpeg = FFMPEGNull()
                elif generate == "overlay":
                    output.unlink(missing_ok=True)
                    ffmpeg = FFMPEGOverlay(
                        ffmpeg=ffmpeg_exe,
                        output=output,
                        options=ffmpeg_options,
                        overlay_size=dimensions,
                        execution=execution,
                    )
                else:
                    output.unlink(missing_ok=True)
                    ffmpeg = FFMPEGOverlayVideo(
                        ffmpeg=ffmpeg_exe,
                        input=inputpath,
                        output=output,
                        options=ffmpeg_options,
                        overlay_size=dimensions,
                        execution=execution,
                    )

                draw_timer = PoorTimer("drawing frames")

                # Draw an overlay frame every 0.1 seconds of video
                timelapse_correction = frame_meta.duration() / video_duration
                log(f"Timelapse Factor = {timelapse_correction:.3f}")
                stepper = frame_meta.stepper(
                    timeunits(seconds=0.1 * timelapse_correction)
                )
                progress = ProgressBarProgress("Render")

                unit_converters = Converters(
                    speed_unit=args.units_speed,
                    distance_unit=args.units_distance,
                    altitude_unit=args.units_altitude,
                    temperature_unit=args.units_temperature,
                )

                layout_creator = create_desired_layout(
                    layout=args.layout,
                    layout_xml=args.layout_xml,
                    dimensions=dimensions,
                    include=args.include,
                    exclude=args.exclude,
                    renderer=renderer,
                    timeseries=frame_meta,
                    font=font,
                    privacy_zone=privacy_zone,
                    profiler=profiler,
                    converters=unit_converters,
                )

                overlay = Overlay(framemeta=frame_meta, create_widgets=layout_creator)

                try:
                    progress.start(len(stepper))
                    with ffmpeg.generate() as writer:

                        if args.double_buffer:
                            log(
                                "*** NOTE: Double Buffer mode is experimental. It is believed to work fine on Linux. "
                                "Please raise issues if you see it working or not-working. Thanks ***"
                            )
                            buffer = DoubleBuffer(dimensions, args.bg, writer)
                        else:
                            buffer = SingleBuffer(dimensions, args.bg, writer)

                        with buffer:
                            for index, dt in enumerate(stepper.steps()):
                                progress.update(index)
                                draw_timer.time(
                                    lambda: buffer.draw(
                                        lambda frame: overlay.draw(dt, frame)
                                    )
                                )

                    log("Finished drawing frames. waiting for ffmpeg to catch up")
                    progress.complete()

                finally:
                    for t in [draw_timer]:
                        log(t)

                    if profiler:
                        log("\n\n*** Widget Timings ***")
                        profiler.print()
                        log("***\n\n")

    except KeyboardInterrupt:
        log("User interrupted...")


if __name__ == "__main__":
    generate_dashboard()